"""
Bank Statement vs Expense Reconciliation Module
- Parses bank statements (Excel/CSV)
- Matches against recorded expenses
- Identifies unrecorded (missing) expenses
- Suggests categories from Category Master
- Maintains full audit trail
"""

from fastapi import APIRouter, UploadFile, File, Form, Body
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

class BulkIgnoreRequest(BaseModel):
    transaction_ids: list[str]
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

# ── Cash Withdrawal Detection (Phase 2) ─────────────────────────────────
# ATM / Cash withdrawals are NOT operating expenses — they only move money
# from bank to wallet. Auto-flag them as "ignored" with a reason so they
# don't pollute reconciliation.
CASH_WITHDRAWAL_PATTERNS = [
    r"\bATM\b",
    r"\bATW\b",
    r"CASH\s*W[DH]L",
    r"CSH\s*W[DH]L",
    r"CASH\s*WITHDRAW",
    r"CASH\s+WD",
    r"\bNFS\b",            # ATM National Financial Switch
    r"\bNWD\b",            # Network Withdrawal
    r"ATM\s*-?\s*CASH",
    r"CW\s*-",
]

def is_cash_withdrawal(narration: str) -> bool:
    """True if the narration looks like an ATM / Cash counter withdrawal."""
    if not narration:
        return False
    upper = narration.upper()
    return any(re.search(p, upper) for p in CASH_WITHDRAWAL_PATTERNS)


# ── Credit Source Detection (Phase 2) ───────────────────────────────────
# Hints that map a credit narration to its likely sales/settlement source.
CREDIT_SOURCE_HINTS = {
    "phonepe": ["PHONEPE", "PHONE PE", "PHONPE"],
    "razorpay": ["RAZORPAY", "RZP", "RAZOR PAY"],
    "swiggy": ["SWIGGY", "BUNDL", "BUNDLE TECH"],
    "zomato": ["ZOMATO", "ZOMATO MEDIA"],
    "doordash": ["DOORDASH", "DASHPASS"],
    "upi": ["UPI/", "UPI-", "UPI ", "@OKICICI", "@OKHDFC", "@OKAXIS", "@OKSBI", "@PAYTM", "@YBL"],
    "card": ["VISA", "MASTERCARD", "RUPAY", "POS ", "MERCHANT", "MDR"],
    "neft_imps": ["NEFT", "IMPS", "RTGS"],
}

def detect_credit_source(narration: str) -> Optional[str]:
    if not narration:
        return None
    upper = narration.upper()
    for source, keys in CREDIT_SOURCE_HINTS.items():
        for k in keys:
            if k in upper:
                return source
    return None


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


def parse_date(val, year_hint=None):
    """Parse date from various formats"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    
    # Standard formats with year
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
    
    # Handle formats without year (e.g., "20 JAN", "21 FEB")
    short_formats = ["%d %b", "%d-%b", "%d %B", "%d-%B"]
    for fmt in short_formats:
        try:
            parsed = datetime.strptime(s, fmt)
            # Use year hint if provided, otherwise current year
            year = year_hint or datetime.now().year
            return parsed.replace(year=year).strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return None


async def parse_pdf_bank_statement(file_content: bytes, filename: str):
    """Parse PDF bank statement using table extraction (for Australian banks like ANZ)"""
    transactions = []
    
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Cannot parse PDF bank statements.")
        return transactions
    
    try:
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            # Try to detect the statement year from first page text
            first_page_text = pdf.pages[0].extract_text() or ""
            year_match = re.search(r'\b(202[4-9]|20[3-9]\d)\b', first_page_text)
            year_hint = int(year_match.group()) if year_match else datetime.now().year
            
            logger.info(f"PDF parsing: {len(pdf.pages)} pages, year hint: {year_hint}")
            
            # Debug: Log raw text from first page to understand PDF structure
            logger.info("=== DEBUG: First page raw text (first 1000 chars) ===")
            logger.info(first_page_text[:1000] if first_page_text else "(empty)")
            logger.info("=== END DEBUG ===")
            
            # Column name mapping - normalize ANZ headers to expected names
            column_mapping = {
                # Date column variations
                'date': 'date',
                'transaction date': 'date',
                'trans date': 'date',
                'value date': 'date',
                
                # Narration/Description column variations
                'narration': 'narration',
                'description': 'narration',
                'details': 'narration',
                'transaction details': 'narration',
                'transaction description': 'narration',
                'particulars': 'narration',
                
                # Debit column variations
                'debit': 'debit',
                'debit amount': 'debit',
                'withdrawal': 'debit',
                'withdrawals': 'debit',
                'money out': 'debit',
                'dr': 'debit',
                
                # Credit column variations (to identify and skip)
                'credit': 'credit',
                'credit amount': 'credit',
                'deposit': 'credit',
                'deposits': 'credit',
                'money in': 'credit',
                'cr': 'credit',
                
                # Balance column
                'balance': 'balance',
                'running balance': 'balance',
            }
            
            all_rows = []
            header_found = False
            col_indices = {}
            
            # Table extraction settings for PDFs without visible grid lines (like ANZ)
            table_settings = {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "snap_tolerance": 3,
                "join_tolerance": 3,
            }
            
            # Extract tables from all pages
            for page_num, page in enumerate(pdf.pages):
                # Try with custom settings first
                tables = page.extract_tables(table_settings=table_settings)
                
                # If no tables found, try default settings
                if not tables:
                    tables = page.extract_tables()
                
                logger.debug(f"Page {page_num + 1}: Found {len(tables) if tables else 0} tables")
                
                for table in tables:
                    if not table:
                        continue
                    
                    for row in table:
                        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                            continue
                        
                        # Clean row data
                        cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                        
                        # Check if this is a header row
                        if not header_found:
                            row_lower = [c.lower() for c in cleaned_row]
                            
                            # Look for header keywords
                            for i, cell in enumerate(row_lower):
                                normalized = column_mapping.get(cell)
                                if normalized:
                                    col_indices[normalized] = i
                            
                            # If we found at least date and (debit or description), this is the header
                            if 'date' in col_indices and ('debit' in col_indices or 'narration' in col_indices):
                                header_found = True
                                logger.info(f"Found header row on page {page_num + 1}: {col_indices}")
                                continue
                        
                        # Process data rows
                        if header_found:
                            all_rows.append(cleaned_row)
            
            logger.info(f"Table extraction: header_found={header_found}, rows_collected={len(all_rows)}")
            
            # If no table found, fall back to text extraction
            if not header_found or not all_rows:
                logger.info("No tables found, falling back to text extraction")
                return await parse_pdf_text_fallback(file_content, filename, year_hint)
            
            # Process extracted rows
            logger.info(f"Processing {len(all_rows)} rows from tables")
            
            skip_patterns = [
                'OPENING BALANCE', 'CLOSING BALANCE', 'BALANCE BROUGHT FORWARD',
                'BALANCE CARRIED FORWARD', 'STATEMENT PERIOD', 'ACCOUNT NUMBER',
                'INTERIM STATEMENT', 'TOTAL'
            ]
            
            for row in all_rows:
                try:
                    # Get date
                    date_idx = col_indices.get('date')
                    if date_idx is None or date_idx >= len(row):
                        continue
                    
                    date_val = row[date_idx]
                    if not date_val:
                        continue
                    
                    # Skip summary rows
                    row_text = ' '.join(row).upper()
                    if any(skip in row_text for skip in skip_patterns):
                        continue
                    
                    # Parse date
                    parsed_date = parse_date(date_val, year_hint)
                    if not parsed_date:
                        continue
                    
                    # Get narration/description
                    narration_idx = col_indices.get('narration')
                    narration = row[narration_idx] if narration_idx is not None and narration_idx < len(row) else ''
                    
                    # Get debit amount
                    debit_idx = col_indices.get('debit')
                    debit_val = row[debit_idx] if debit_idx is not None and debit_idx < len(row) else ''
                    debit_amount = parse_amount(debit_val) if debit_val else 0
                    
                    # Get credit amount (to skip credit transactions)
                    credit_idx = col_indices.get('credit')
                    credit_val = row[credit_idx] if credit_idx is not None and credit_idx < len(row) else ''
                    credit_amount = parse_amount(credit_val) if credit_val else 0
                    
                    # Skip pure zero-amount rows
                    if debit_amount <= 0 and credit_amount <= 0:
                        continue

                    if not narration or len(narration) < 3:
                        narration = "Transaction"

                    txn_type = "debit" if debit_amount > 0 else "credit"
                    transactions.append({
                        "transaction_id": str(uuid.uuid4())[:12],
                        "transaction_date": parsed_date,
                        "narration": narration,
                        "debit_amount": debit_amount,
                        "credit_amount": credit_amount,
                        "txn_type": txn_type,
                        "reference_number": "",
                        "balance": None,
                    })
                    
                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue
        
        logger.info(f"PDF table extraction: {len(transactions)} debit+credit transactions from {filename}")
        
        # If table extraction found 0 transactions, fall back to text parsing
        if not transactions:
            logger.info("Table extraction yielded 0 transactions, falling back to text parser")
            return await parse_pdf_text_fallback(file_content, filename, year_hint)
        
    except Exception as e:
        logger.error(f"Error parsing PDF bank statement: {e}")
    
    return transactions


async def parse_pdf_text_fallback(file_content: bytes, filename: str, year_hint: int):
    """Fallback text-based PDF parsing when table extraction fails"""
    transactions = []
    
    try:
        import pdfplumber
        
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            all_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                all_text += page_text + "\n"
        
        skip_patterns = [
            'OPENING BALANCE', 'CLOSING BALANCE', 'BALANCE BROUGHT FORWARD',
            'BALANCE CARRIED FORWARD', 'STATEMENT PERIOD', 'ACCOUNT NUMBER',
            'INTERIM STATEMENT', 'TRANSACTION DESCRIPTION', 'TRANSACTION DETAILS',
            'WITHDRAWALS ($)', 'DEPOSITS ($)', 'BALANCE ($)', 'NEED TO GET IN TOUCH',
            'WELCOME TO YOUR', 'ACCOUNT DETAILS', 'TOTAL DEPOSITS', 'TOTAL WITHDRAWALS'
        ]
        
        lines = all_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header/summary lines
            line_upper = line.upper()
            if any(skip in line_upper for skip in skip_patterns):
                continue
            
            # Pattern 1: "21 JAN DESCRIPTION... 6.61 blank 8,951.07" (ANZ format with blank)
            # Pattern 2: "20 FEB DESCRIPTION... $90.54" (older format)
            # Match date at start: DD MMM or DD/MM format
            date_match = re.match(r'^(\d{1,2}\s+[A-Z]{3}|\d{1,2}/\d{1,2})\s+(.+)', line, re.IGNORECASE)
            if not date_match:
                continue
            
            date_str = date_match.group(1).upper()
            rest = date_match.group(2)
            
            parsed_date = parse_date(date_str, year_hint)
            if not parsed_date:
                continue
            
            # For ANZ format: look for withdrawal amount (number followed by "blank")
            # Pattern: "description 6.61 blank 8,951.07" -> withdrawal is 6.61
            withdrawal_match = re.search(r'([\d,]+\.\d{2})\s+blank\s+[\d,]+\.\d{2}', rest, re.IGNORECASE)
            
            if withdrawal_match:
                # ANZ format with "blank" markers
                amount = parse_amount(withdrawal_match.group(1))
                narration = rest[:withdrawal_match.start()].strip()
            else:
                # Standard format: amount at end
                amount_match = re.search(r'[\$]?\s*([\d,]+\.\d{2})\s*$', rest)
                if not amount_match:
                    amount_match = re.search(r'([\d,]+\.\d{2})', rest)
                    if not amount_match:
                        continue
                
                amount = parse_amount(amount_match.group(1))
                narration = rest[:amount_match.start()].strip() if amount_match.start() > 0 else rest
                narration = re.sub(r'[\d,]+\.\d{2}', '', narration).strip()
            
            if amount == 0 or amount > 1000000:
                continue
            
            if len(narration) < 3:
                continue
            
            # Skip credits based on narration keywords
            is_credit = any(kw in narration.upper() for kw in [
                'TRANSFER FROM', 'FROM ANZ', 'FROM AMEX', 'FROM 273',
                'DEPOSIT', 'CREDIT', 'REFUND', 'INTEREST PAID',
                'TAX REFUND', 'REVERSAL', 'REBATE'
            ])
            
            # Also check if it's clearly a deposit (in ANZ format, deposits have "blank" before the amount)
            deposit_match = re.search(r'blank\s+([\d,]+\.\d{2})\s+[\d,]+\.\d{2}', rest, re.IGNORECASE)
            if deposit_match:
                is_credit = True
            
            # Phase 2: keep credits (don't skip) — flag them as txn_type=credit so
            # they can be reconciled against sales/settlements instead of expenses.
            
            # Skip header/footer text
            if any(kw in narration.upper() for kw in ['TELEPHONE', 'ENQUIRIES', 'PAGE', 'ACCOUNT TYPE', 'EFFECTIVE DATE']):
                continue
            
            # Clean up narration - remove "EFFECTIVE DATE" suffix
            narration = re.sub(r'\s*EFFECTIVE DATE.*$', '', narration, flags=re.IGNORECASE).strip()

            transactions.append({
                "transaction_id": str(uuid.uuid4())[:12],
                "transaction_date": parsed_date,
                "narration": narration,
                "debit_amount": 0.0 if is_credit else amount,
                "credit_amount": amount if is_credit else 0.0,
                "txn_type": "credit" if is_credit else "debit",
                "reference_number": "",
                "balance": None,
            })
        
        logger.info(f"PDF text fallback: {len(transactions)} debit+credit transactions from {filename}")
        
    except Exception as e:
        logger.error(f"Error in PDF text fallback: {e}")
    
    return transactions


def detect_columns(headers):
    """Auto-detect column mappings from headers"""
    mapping = {"date": None, "narration": None, "debit": None, "credit": None, "reference": None, "balance": None}

    headers_upper = [str(h).upper().strip() if h else "" for h in headers]

    date_keywords = ["TRANSACTION DATE", "TXN DATE", "DATE", "VALUE DATE", "POSTING DATE", "TXN DT"]
    narr_keywords = ["NARRATION", "DESCRIPTION", "PARTICULARS", "REMARKS", "DETAILS", "TRANSACTION DETAILS", "TRANSACTION DESCRIPTION"]
    debit_keywords = ["DEBIT", "WITHDRAWAL", "DR", "DEBIT AMOUNT", "WITHDRAWALS", "DR AMOUNT", "DEBIT/WITHDRAWAL"]
    credit_keywords = ["CREDIT", "DEPOSIT", "CR", "CREDIT AMOUNT", "DEPOSITS", "CR AMOUNT", "CREDIT/DEPOSIT"]
    ref_keywords = ["REFERENCE", "REF NO", "CHQ NO", "CHEQUE NO", "UTR", "REFERENCE NO", "CHEQUE NO."]
    bal_keywords = ["BALANCE", "CLOSING BALANCE", "RUNNING BALANCE"]

    for i, h in enumerate(headers_upper):
        if not h:
            continue
        # Check for exact or partial matches
        if not mapping["date"]:
            for k in date_keywords:
                if k in h or h == k:
                    mapping["date"] = i
                    break
        if not mapping["narration"]:
            for k in narr_keywords:
                if k in h or h == k:
                    mapping["narration"] = i
                    break
        if not mapping["debit"]:
            for k in debit_keywords:
                if k in h or h == k:
                    mapping["debit"] = i
                    break
        if not mapping["credit"]:
            for k in credit_keywords:
                if k in h or h == k:
                    mapping["credit"] = i
                    break
        if not mapping["reference"]:
            for k in ref_keywords:
                if k in h or h == k:
                    mapping["reference"] = i
                    break
        if not mapping["balance"]:
            for k in bal_keywords:
                if k in h or h == k:
                    mapping["balance"] = i
                    break

    return mapping


async def parse_bank_statement(file_content: bytes, filename: str):
    """Parse bank statement from Excel, CSV, or PDF"""
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

        # Find header row - search first 50 rows for date-like header (bank statements often have info at top)
        header_idx = None
        header_keywords = ["TRANSACTION DATE", "TXN DATE", "VALUE DATE", "PARTICULARS", "NARRATION", "DESCRIPTION", "DEBIT", "WITHDRAWAL"]
        for i, row in enumerate(rows[:50]):
            row_str = " ".join(str(c).upper() for c in row if c)
            matches = sum(1 for k in header_keywords if k in row_str)
            if matches >= 2:  # Need at least 2 matches (date + narration or date + debit)
                header_idx = i
                break

        if header_idx is None:
            logger.warning(f"Could not find header row in Excel file: {filename}")
            return transactions

        headers = rows[header_idx]
        mapping = detect_columns(headers)
        data_rows = rows[header_idx + 1:]
        logger.info(f"Excel parsing - Header at row {header_idx}: {headers}")
        logger.info(f"Column mapping: {mapping}")

    elif filename.lower().endswith(".csv"):
        text = file_content.decode("utf-8", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if len(rows) < 2:
            return transactions

        header_idx = None
        header_keywords = ["TRANSACTION DATE", "TXN DATE", "VALUE DATE", "PARTICULARS", "NARRATION", "DESCRIPTION", "DEBIT", "WITHDRAWAL"]
        for i, row in enumerate(rows[:50]):
            row_str = " ".join(str(c).upper() for c in row if c)
            matches = sum(1 for k in header_keywords if k in row_str)
            if matches >= 2:
                header_idx = i
                break

        if header_idx is None:
            return transactions

        headers = rows[header_idx]
        mapping = detect_columns(headers)
        data_rows = rows[header_idx + 1:]

    elif filename.lower().endswith(".pdf"):
        # Parse PDF bank statement (for Australia)
        transactions = await parse_pdf_bank_statement(file_content, filename)
        return transactions
    else:
        return transactions

    if mapping["date"] is None or (mapping["debit"] is None and mapping["credit"] is None):
        logger.warning(f"Missing required columns. Mapping: {mapping}")
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

            # Phase 2: keep both credits and debits. Only skip zero-amount rows.
            if debit_amount == 0 and credit_amount == 0:
                continue

            txn_type = "debit" if debit_amount > 0 else "credit"
            transactions.append({
                "transaction_id": str(uuid.uuid4())[:12],
                "transaction_date": parsed_date,
                "narration": str(narr_val or "").strip(),
                "debit_amount": debit_amount,
                "credit_amount": credit_amount,
                "txn_type": txn_type,
                "reference_number": str(ref_val or "").strip(),
                "balance": parse_amount(bal_val) if bal_val else None,
            })
        except (IndexError, TypeError):
            continue

    return transactions


# ── Matching Logic (Phase 2) ────────────────────────────────────────────
# Status taxonomy (per user directive 2026-02):
#   matched               — exact date + exact amount hit
#   partially_matched     — exact amount but fuzzy date (±2 days), OR
#                           exact date with amount drift ≤5%
#   unrecorded / unmatched — no candidate found (legacy "unrecorded" kept
#                            for backward compatibility with existing UI)
#   ignored               — auto-flagged ATM/cash withdrawal OR user-ignored
#   manual_review         — high-value (≥ ₹50k) unmatched debit/credit OR
#                           credit that hit multiple equally-likely sources
HIGH_VALUE_THRESHOLD = 50000.0
PARTIAL_AMOUNT_DRIFT_PCT = 0.05  # ±5%


async def _load_credit_sources(center: str, month: str):
    """Build a list of expected bank credits from sales + commission data.
    Each entry: {date, amount, source, description}.
    """
    try:
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        end_date = f"{int(year) + 1}-01-01" if int(mon) == 12 else f"{year}-{int(mon) + 1:02d}-01"
    except Exception:
        return []

    credits: list = []

    # Daily sales (cash deposits, online / card, aggregator gross)
    try:
        sales = await db.daily_sales.find(
            {"center": center, "date": {"$gte": start_date, "$lt": end_date}},
            {"_id": 0},
        ).to_list(500)
        for s in sales:
            d = s.get("date")
            cash = float(s.get("total_cash_sale") or s.get("cash_sale") or 0)
            online = float(s.get("total_online_sale") or s.get("online_sale") or s.get("card_sale") or 0)
            swiggy = float(s.get("swiggy_sale") or s.get("swiggy") or 0)
            zomato = float(s.get("zomato_sale") or s.get("zomato") or 0)
            doordash = float(s.get("doordash_sale") or s.get("doordash") or 0)
            phonepe = float(s.get("phonepe_sale") or s.get("phonepe") or 0)
            if cash > 0:
                credits.append({"date": d, "amount": round(cash, 2),
                                "source": "cash_sales", "description": "Cash sales deposit"})
            if online > 0:
                credits.append({"date": d, "amount": round(online, 2),
                                "source": "card", "description": "Card / Online sales"})
            if phonepe > 0:
                credits.append({"date": d, "amount": round(phonepe, 2),
                                "source": "phonepe", "description": "PhonePe daily sales"})
            for plat, val in (("swiggy", swiggy), ("zomato", zomato), ("doordash", doordash)):
                if val > 0:
                    credits.append({"date": d, "amount": round(val, 2),
                                    "source": plat, "description": f"{plat.title()} order receipts"})
    except Exception as e:
        logger.warning(f"_load_credit_sources daily_sales: {e}")

    # Monthly commission settlements (PhonePe / Razorpay / Aggregator nets)
    try:
        commission_rows = await db.monthly_commissions.find(
            {"center": center, "month": month}, {"_id": 0}
        ).to_list(500)
        for c in commission_rows:
            net = float(c.get("net_settlement_amount") or c.get("net_amount") or 0)
            if net <= 0:
                continue
            platform = (c.get("platform") or "").lower()
            settlement_date = c.get("settlement_date") or c.get("date") or f"{year}-{mon}-15"
            credits.append({
                "date": settlement_date,
                "amount": round(net, 2),
                "source": platform or "settlement",
                "description": f"{platform.title()} net settlement",
                "pg_commission": float(c.get("sundry_debtors") or 0),
                "gst_on_commission": float(c.get("gst_tax_deductions") or 0),
            })
    except Exception as e:
        logger.warning(f"_load_credit_sources monthly_commissions: {e}")

    return credits


def _amount_close(a: float, b: float, drift_pct: float = PARTIAL_AMOUNT_DRIFT_PCT) -> bool:
    if a <= 0 or b <= 0:
        return False
    return abs(a - b) <= max(a, b) * drift_pct


async def match_transactions(transactions: list, center: str, month: str):
    """Match bank transactions against expenses (debits) and sales/settlements (credits).

    Returns dict with buckets: matched, partially_matched, unmatched_debits,
    unmatched_credits, ignored, manual_review, plus full lists for storage.
    """
    try:
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        if int(mon) == 12:
            end_date = f"{int(year) + 1}-01-01"
        else:
            end_date = f"{year}-{int(mon) + 1:02d}-01"
    except Exception:
        return {"all": transactions}

    # ── Expenses pool (for debits) ──────────────────────────────────────
    expenses = await db.expenses.find({
        "center": center,
        "date": {"$gte": start_date, "$lt": end_date}
    }, {"_id": 0}).to_list(5000)

    expense_lookup: dict = {}
    amount_lookup: dict = {}
    for exp in expenses:
        amt = round(float(exp.get("amount", 0) or 0), 2)
        key = (exp.get("date", ""), amt)
        expense_lookup.setdefault(key, []).append(exp)
        amount_lookup.setdefault(amt, []).append(exp)

    # ── Credit pool (for credits) ───────────────────────────────────────
    credit_pool = await _load_credit_sources(center, month)
    credit_by_key: dict = {}
    credit_by_amount: dict = {}
    for c in credit_pool:
        amt = round(c["amount"], 2)
        credit_by_key.setdefault((c.get("date", ""), amt), []).append(c)
        credit_by_amount.setdefault(amt, []).append(c)

    matched: list = []
    partially_matched: list = []
    unmatched_debits: list = []
    unmatched_credits: list = []
    ignored: list = []
    manual_review: list = []

    for txn in transactions:
        txn_type = txn.get("txn_type") or ("credit" if (txn.get("credit_amount") or 0) > 0 else "debit")
        narration = txn.get("narration", "")
        debit_amt = round(float(txn.get("debit_amount") or 0), 2)
        credit_amt = round(float(txn.get("credit_amount") or 0), 2)
        txn_date = txn.get("transaction_date", "")
        txn["txn_type"] = txn_type

        # ── Auto-ignore ATM / Cash withdrawal ─────────────────────────
        if txn_type == "debit" and is_cash_withdrawal(narration):
            txn["match_status"] = "ignored"
            txn["recon_status"] = "ignored"
            txn["ignore_reason"] = "Cash Withdrawal (auto)"
            txn["auto_ignored"] = True
            ignored.append(txn)
            continue

        amount_for_match = debit_amt if txn_type == "debit" else credit_amt

        if txn_type == "debit":
            # 1. Exact date + amount
            key = (txn_date, amount_for_match)
            if key in expense_lookup and expense_lookup[key]:
                exp = expense_lookup[key].pop(0)
                amount_lookup.get(amount_for_match, []).remove(exp) if exp in amount_lookup.get(amount_for_match, []) else None
                txn["match_status"] = "matched"
                txn["recon_status"] = "matched"
                txn["matched_expense"] = {
                    "description": exp.get("description", ""),
                    "expense_type": exp.get("expense_type", ""),
                    "payment_mode": exp.get("payment_mode", ""),
                    "date": exp.get("date", ""),
                    "amount": exp.get("amount", 0),
                }
                txn["match_method"] = "exact_date_amount"
                matched.append(txn)
                continue

            # 2. Partial match — exact amount, fuzzy date (±2 days)
            partial_hit = None
            if amount_for_match in amount_lookup:
                try:
                    txn_dt = datetime.strptime(txn_date, "%Y-%m-%d")
                    for exp in amount_lookup[amount_for_match]:
                        try:
                            exp_dt = datetime.strptime(exp.get("date", ""), "%Y-%m-%d")
                            if abs((txn_dt - exp_dt).days) <= 2:
                                partial_hit = (exp, "fuzzy_date_exact_amount")
                                break
                        except ValueError:
                            continue
                except ValueError:
                    pass

            # 3. Partial match — exact date, amount drift ≤5%
            if not partial_hit:
                for amt_key, exps in amount_lookup.items():
                    if not _amount_close(amt_key, amount_for_match):
                        continue
                    for exp in exps:
                        if exp.get("date", "") == txn_date:
                            partial_hit = (exp, "exact_date_fuzzy_amount")
                            break
                    if partial_hit:
                        break

            if partial_hit:
                exp, method = partial_hit
                amount_lookup[round(float(exp.get("amount", 0) or 0), 2)].remove(exp)
                txn["match_status"] = "partially_matched"
                txn["recon_status"] = "partially_matched"
                txn["matched_expense"] = {
                    "description": exp.get("description", ""),
                    "expense_type": exp.get("expense_type", ""),
                    "payment_mode": exp.get("payment_mode", ""),
                    "date": exp.get("date", ""),
                    "amount": exp.get("amount", 0),
                }
                txn["match_method"] = method
                partially_matched.append(txn)
                continue

            # 4. Manual review (high value) or unmatched
            if amount_for_match >= HIGH_VALUE_THRESHOLD:
                txn["match_status"] = "manual_review"
                txn["recon_status"] = "manual_review"
                txn["matched_expense"] = None
                txn["match_method"] = None
                manual_review.append(txn)
            else:
                # Legacy "unrecorded" preserved so existing UI continues to work
                txn["match_status"] = "unrecorded"
                txn["recon_status"] = "unmatched"
                txn["matched_expense"] = None
                txn["match_method"] = None
                unmatched_debits.append(txn)
            continue

        # ── CREDIT side ───────────────────────────────────────────────
        # 1. Exact date + amount against credit pool
        key = (txn_date, amount_for_match)
        if key in credit_by_key and credit_by_key[key]:
            c = credit_by_key[key].pop(0)
            credit_by_amount.get(amount_for_match, []).remove(c) if c in credit_by_amount.get(amount_for_match, []) else None
            txn["match_status"] = "matched"
            txn["recon_status"] = "matched"
            txn["matched_credit"] = c
            txn["match_method"] = "exact_date_amount_credit"
            matched.append(txn)
            continue

        # 2. Partial — exact amount, fuzzy date (±3 days for settlements)
        partial_hit = None
        if amount_for_match in credit_by_amount:
            try:
                txn_dt = datetime.strptime(txn_date, "%Y-%m-%d")
                for c in credit_by_amount[amount_for_match]:
                    try:
                        c_dt = datetime.strptime(c.get("date", ""), "%Y-%m-%d")
                        if abs((txn_dt - c_dt).days) <= 3:
                            partial_hit = (c, "fuzzy_date_exact_amount_credit")
                            break
                    except ValueError:
                        continue
            except ValueError:
                pass

        # 3. Partial — exact date, amount drift ≤5%
        if not partial_hit:
            for amt_key, lst in credit_by_amount.items():
                if not _amount_close(amt_key, amount_for_match):
                    continue
                for c in lst:
                    if c.get("date", "") == txn_date:
                        partial_hit = (c, "exact_date_fuzzy_amount_credit")
                        break
                if partial_hit:
                    break

        if partial_hit:
            c, method = partial_hit
            credit_by_amount[round(c["amount"], 2)].remove(c)
            txn["match_status"] = "partially_matched"
            txn["recon_status"] = "partially_matched"
            txn["matched_credit"] = c
            txn["match_method"] = method
            partially_matched.append(txn)
            continue

        # 4. Tag the inferred credit source for analyst review
        txn["credit_source_hint"] = detect_credit_source(narration)
        if amount_for_match >= HIGH_VALUE_THRESHOLD:
            txn["match_status"] = "manual_review"
            txn["recon_status"] = "manual_review"
            manual_review.append(txn)
        else:
            txn["match_status"] = "unrecorded_credit"
            txn["recon_status"] = "unmatched"
            unmatched_credits.append(txn)

    return {
        "matched": matched,
        "partially_matched": partially_matched,
        "unmatched_debits": unmatched_debits,
        "unmatched_credits": unmatched_credits,
        "ignored": ignored,
        "manual_review": manual_review,
    }


# ── API Endpoints ───────────────────────────────────────────────────────

@router.post("/upload")
async def upload_bank_statement(
    file: UploadFile = File(...),
    center: str = Form(...),
    month: str = Form(...),
    bank_account: str = Form(""),
    token: str = Form(""),
):
    """Upload and parse a bank statement, then run reconciliation"""
    print(f"[BANK_RECON] Upload request: center={center}, month={month}, token_present={bool(token)}", flush=True)
    logger.info(f"Upload request: center={center}, month={month}, token_present={bool(token)}")
    
    session = await _get_session(token)
    if not session:
        print("[BANK_RECON] Auth failed - token empty or invalid", flush=True)
        logger.warning(f"Authentication failed for token: {token[:10] if token else 'empty'}...")
        return {"detail": "Authentication required"}

    content = await file.read()
    print(f"[BANK_RECON] Received file: {file.filename}, size={len(content)} bytes", flush=True)
    logger.info(f"Received file: {file.filename}, size={len(content)} bytes")
    
    if len(content) > 10 * 1024 * 1024:
        return {"detail": "File too large (max 10MB)"}
    
    if len(content) == 0:
        print("[BANK_RECON] ERROR: File is empty!", flush=True)
        return {"detail": "File is empty. Please select a valid file."}

    # Persist the raw bank statement so it can be re-downloaded later
    # (Franchise Owner Reports → Raw Uploaded Files / Email Pack ZIP).
    raw_stored_path: Optional[str] = None
    try:
        import os as _os
        raw_dir = f"/app/backend/raw_uploads/bank_statements/{center}/{month}"
        _os.makedirs(raw_dir, exist_ok=True)
        raw_filename = f"{uuid.uuid4().hex}_{file.filename}"
        raw_stored_path = f"{raw_dir}/{raw_filename}"
        with open(raw_stored_path, "wb") as _f:
            _f.write(content)
        await db.raw_uploads.insert_one({
            "raw_id": str(uuid.uuid4()),
            "kind": "bank_statement",
            "platform": "bank",
            "center": center,
            "month": month,
            "original_filename": file.filename,
            "stored_path": raw_stored_path,
            "size_bytes": len(content),
            "bank_account": bank_account,
            "uploaded_by": (session or {}).get("managerName", "Unknown"),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as _ex:
        logger.warning(f"raw bank-recon file storage failed for {center} {month}: {_ex}")

    # Parse bank statement
    try:
        transactions = await parse_bank_statement(content, file.filename)
        print(f"[BANK_RECON] Parsed {len(transactions)} transactions from {file.filename}", flush=True)
        logger.info(f"Parsed {len(transactions)} transactions from {file.filename}")
    except Exception as e:
        print(f"[BANK_RECON] ERROR parsing: {e}", flush=True)
        logger.error(f"Error parsing bank statement: {e}", exc_info=True)
        return {"detail": f"Error parsing file: {str(e)}"}
    
    if not transactions:
        print(f"[BANK_RECON] WARNING: No transactions parsed from {file.filename} (size={len(content)} bytes)", flush=True)
        logger.warning(f"No transactions parsed from {file.filename} (size={len(content)} bytes)")
        return {"detail": "Could not parse any transactions from the file. Ensure it has Date, Narration, and Debit columns."}

    # Run matching (Phase 2 — handles credits + debits + auto-ignore)
    buckets = await match_transactions(transactions, center, month)
    matched = buckets["matched"]
    partially_matched = buckets["partially_matched"]
    unmatched_debits = buckets["unmatched_debits"]
    unmatched_credits = buckets["unmatched_credits"]
    auto_ignored = buckets["ignored"]
    manual_review = buckets["manual_review"]

    # Combined unrecorded list (for legacy UI tab) = unmatched debits + manual review debits
    unrecorded = unmatched_debits + [t for t in manual_review if t.get("txn_type") == "debit"]

    # Suggest categories for unrecorded debits + manual review items
    for txn in unrecorded + [t for t in manual_review if t.get("txn_type") == "credit"]:
        if txn.get("txn_type") == "debit":
            txn["suggested_category"] = await suggest_category(txn.get("narration", ""))
    for txn in unmatched_credits:
        # Surface the inferred credit source as the "suggested category" so the
        # analyst can see at a glance whether it looks like PhonePe/Razorpay/etc.
        if not txn.get("suggested_category"):
            txn["suggested_category"] = txn.get("credit_source_hint") or ""

    # Create upload record
    upload_id = str(uuid.uuid4())[:16]
    all_txns = matched + partially_matched + unmatched_debits + unmatched_credits + auto_ignored + manual_review
    total_credit = round(sum((t.get("credit_amount") or 0) for t in all_txns), 2)
    total_debit = round(sum((t.get("debit_amount") or 0) for t in all_txns), 2)
    upload_record = {
        "upload_id": upload_id,
        "filename": file.filename,
        "center": center,
        "month": month,
        "bank_account": bank_account,
        "total_transactions": len(all_txns),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "matched_count": len(matched),
        "partially_matched_count": len(partially_matched),
        "unmatched_debit_count": len(unmatched_debits),
        "unmatched_credit_count": len(unmatched_credits),
        "auto_ignored_count": len(auto_ignored),
        "manual_review_count": len(manual_review),
        "unrecorded_count": len(unrecorded),  # legacy field kept for old UI
        "uploaded_by": session.get("name", session.get("mobile", "Unknown")),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "reconciled",
    }
    await db.bank_statement_uploads.insert_one(upload_record)

    # Store transactions
    for txn in all_txns:
        txn["upload_id"] = upload_id
        txn["center"] = center
        txn["month"] = month
    if all_txns:
        await db.bank_transactions.insert_many(
            [{k: v for k, v in t.items()} for t in all_txns]
        )

    # Reconciliation log
    await db.expense_reconciliation_log.insert_one({
        "upload_id": upload_id,
        "action": "upload_and_reconcile",
        "center": center,
        "month": month,
        "matched_count": len(matched),
        "partially_matched_count": len(partially_matched),
        "unmatched_debit_count": len(unmatched_debits),
        "unmatched_credit_count": len(unmatched_credits),
        "auto_ignored_count": len(auto_ignored),
        "manual_review_count": len(manual_review),
        "unrecorded_count": len(unrecorded),
        "action_taken_by": session.get("name", session.get("mobile", "")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Calculate summary
    total_bank_debit = round(sum((t.get("debit_amount") or 0) for t in all_txns), 2)
    total_bank_credit = round(sum((t.get("credit_amount") or 0) for t in all_txns), 2)
    total_matched = round(sum((t.get("debit_amount") or 0) + (t.get("credit_amount") or 0) for t in matched), 2)
    total_partially_matched = round(sum((t.get("debit_amount") or 0) + (t.get("credit_amount") or 0) for t in partially_matched), 2)
    total_unmatched_debit = round(sum((t.get("debit_amount") or 0) for t in unmatched_debits), 2)
    total_unmatched_credit = round(sum((t.get("credit_amount") or 0) for t in unmatched_credits), 2)
    total_ignored = round(sum((t.get("debit_amount") or 0) for t in auto_ignored), 2)
    total_manual_review = round(sum((t.get("debit_amount") or 0) + (t.get("credit_amount") or 0) for t in manual_review), 2)

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
            "total_bank_credits": total_bank_credit,
            "total_expenses_recorded": recorded_total,
            "total_bank_transactions": len(all_txns),
            "recorded_expense_count": recorded_count,
            "matched_count": len(matched),
            "matched_amount": total_matched,
            "partially_matched_count": len(partially_matched),
            "partially_matched_amount": total_partially_matched,
            "unmatched_debit_count": len(unmatched_debits),
            "unmatched_debit_amount": total_unmatched_debit,
            "unmatched_credit_count": len(unmatched_credits),
            "unmatched_credit_amount": total_unmatched_credit,
            "auto_ignored_count": len(auto_ignored),
            "auto_ignored_amount": total_ignored,
            "manual_review_count": len(manual_review),
            "manual_review_amount": total_manual_review,
            # Legacy fields kept for backward compat with existing UI
            "unrecorded_count": len(unrecorded),
            "unrecorded_amount": total_unmatched_debit,
        },
        "matched": [{k: v for k, v in t.items() if k != "_id"} for t in matched],
        "partially_matched": [{k: v for k, v in t.items() if k != "_id"} for t in partially_matched],
        "unmatched_credits": [{k: v for k, v in t.items() if k != "_id"} for t in unmatched_credits],
        "auto_ignored": [{k: v for k, v in t.items() if k != "_id"} for t in auto_ignored],
        "manual_review": [{k: v for k, v in t.items() if k != "_id"} for t in manual_review],
        "unrecorded": [{k: v for k, v in t.items() if k != "_id"} for t in unrecorded],  # legacy
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


@router.post("/bulk-ignore")
async def bulk_ignore_transactions(req: BulkIgnoreRequest):
    """Mark multiple transactions as intentionally ignored in one shot."""
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}
    if not req.transaction_ids:
        return {"detail": "No transactions selected"}

    result = await db.bank_transactions.update_many(
        {"transaction_id": {"$in": req.transaction_ids}, "upload_id": req.upload_id},
        {"$set": {"match_status": "ignored", "ignore_reason": req.reason or ""}},
    )
    actor = session.get("name", session.get("mobile", ""))
    now_iso = datetime.now(timezone.utc).isoformat()
    if result.modified_count:
        await db.expense_reconciliation_log.insert_many([
            {
                "upload_id": req.upload_id,
                "bank_transaction_id": tid,
                "action": "ignore",
                "reason": req.reason or "",
                "reconciliation_status": "ignored",
                "action_taken_by": actor,
                "timestamp": now_iso,
            } for tid in req.transaction_ids
        ])
    return {
        "success": True,
        "message": f"{result.modified_count} transaction(s) ignored",
        "ignored_count": result.modified_count,
    }


@router.post("/reset-transaction")
async def reset_transaction(req: dict = Body(...)):
    """Undo a previous Add/Ignore on a bank transaction.
       - If status='added': delete the linked expense row, mark txn as 'unrecorded'.
       - If status='ignored': clear ignore_reason, mark txn as 'unrecorded'.
    """
    token = req.get("token")
    upload_id = req.get("upload_id")
    transaction_id = req.get("transaction_id")
    session = await _get_session(token)
    if not session:
        return {"detail": "Authentication required"}
    if not upload_id or not transaction_id:
        return {"detail": "upload_id and transaction_id are required"}

    txn = await db.bank_transactions.find_one(
        {"transaction_id": transaction_id, "upload_id": upload_id}, {"_id": 0}
    )
    if not txn:
        return {"detail": "Transaction not found"}

    actor = session.get("name", session.get("mobile", ""))
    now_iso = datetime.now(timezone.utc).isoformat()
    prev_status = txn.get("match_status")
    expense_id = txn.get("added_expense_id")

    # If it was added, delete the expense row first
    if prev_status == "added" and expense_id:
        try:
            from bson import ObjectId
            await db.expenses.delete_one({"expense_id": expense_id})
            # Also try by _id if expense_id field wasn't set on legacy rows
            try:
                await db.expenses.delete_one({"_id": ObjectId(expense_id)})
            except Exception:
                pass
        except Exception:
            pass

    await db.bank_transactions.update_one(
        {"transaction_id": transaction_id, "upload_id": upload_id},
        {"$set": {"match_status": "unrecorded"},
         "$unset": {"added_expense_id": "", "ignore_reason": ""}}
    )
    await db.expense_reconciliation_log.insert_one({
        "upload_id": upload_id,
        "bank_transaction_id": transaction_id,
        "previous_status": prev_status,
        "deleted_expense_id": expense_id if prev_status == "added" else None,
        "action": "reset",
        "reconciliation_status": "unrecorded",
        "action_taken_by": actor,
        "timestamp": now_iso,
    })
    return {"success": True, "message": "Transaction reset to unrecorded"}


@router.post("/bulk-add-expense")
async def bulk_add_expense(req: dict = Body(...)):
    """Add multiple unrecorded bank transactions as expenses in one go.
       Useful when many txns share the same narration (Salary, Card 2473, etc.).
       Body: { token, upload_id, transaction_ids: [...], expense_type, payment_mode, description }
       Each txn gets its own expense row with its own debit amount and date.
    """
    token = req.get("token")
    session = await _get_session(token)
    if not session:
        return {"detail": "Authentication required"}

    upload_id = req.get("upload_id")
    txn_ids = req.get("transaction_ids") or []
    expense_type = req.get("expense_type")
    payment_mode = req.get("payment_mode") or "Bank Transfer"
    common_description = (req.get("description") or "").strip()

    if not upload_id or not txn_ids or not expense_type:
        return {"detail": "upload_id, transaction_ids and expense_type are required"}

    # Validate category once
    cat_exists = await db.expense_heads.find_one({"name": expense_type, "is_active": {"$ne": False}})
    if not cat_exists:
        return {"detail": f"Category '{expense_type}' not found in Category Master"}

    actor = session.get("name", session.get("mobile", ""))
    added = 0
    skipped = 0
    errors: List[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for tid in txn_ids:
        try:
            txn = await db.bank_transactions.find_one(
                {"transaction_id": tid, "upload_id": upload_id}, {"_id": 0}
            )
            if not txn:
                skipped += 1
                errors.append(f"{tid}: not found")
                continue
            if txn.get("match_status") == "added":
                skipped += 1
                continue
            expense_id = str(uuid.uuid4())[:16]
            await db.expenses.insert_one({
                "expense_id": expense_id,
                "center": txn["center"],
                "date": txn["transaction_date"],
                # Use common description if provided, else the txn's own narration
                "description": common_description or txn.get("narration", ""),
                "amount": txn["debit_amount"],
                "expense_type": expense_type,
                "payment_mode": payment_mode,
                "reference_number": txn.get("reference_number", ""),
                "source": "bank_reconciliation_bulk",
                "bank_upload_id": upload_id,
                "bank_transaction_id": tid,
                "created_by": actor,
                "created_at": now_iso,
            })
            await db.bank_transactions.update_one(
                {"transaction_id": tid, "upload_id": upload_id},
                {"$set": {"match_status": "added", "added_expense_id": expense_id}}
            )
            await db.expense_reconciliation_log.insert_one({
                "upload_id": upload_id,
                "bank_transaction_id": tid,
                "matched_expense_id": expense_id,
                "suggested_category": txn.get("suggested_category"),
                "final_category": expense_type,
                "action": "bulk_add_expense",
                "reconciliation_status": "added",
                "action_taken_by": actor,
                "timestamp": now_iso,
            })
            added += 1
        except Exception as e:
            errors.append(f"{tid}: {str(e)[:80]}")
            skipped += 1

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors[:20],
        "message": f"Bulk add complete: {added} expense(s) created, {skipped} skipped"
    }


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
    partially_matched = [t for t in transactions if t.get("match_status") == "partially_matched"]
    unrecorded = [t for t in transactions if t.get("match_status") == "unrecorded"]
    unmatched_credits = [t for t in transactions if t.get("match_status") == "unrecorded_credit"]
    added = [t for t in transactions if t.get("match_status") == "added"]
    ignored = [t for t in transactions if t.get("match_status") == "ignored"]
    manual_review = [t for t in transactions if t.get("match_status") == "manual_review"]

    def _sum(rows, field):
        return round(sum((t.get(field) or 0) for t in rows), 2)

    return {
        "success": True,
        "upload": upload,
        "summary": {
            "total_transactions": len(transactions),
            "total_bank_debits": _sum(transactions, "debit_amount"),
            "total_bank_credits": _sum(transactions, "credit_amount"),
            "matched_count": len(matched),
            "matched_amount": _sum(matched, "debit_amount") + _sum(matched, "credit_amount"),
            "partially_matched_count": len(partially_matched),
            "partially_matched_amount": _sum(partially_matched, "debit_amount") + _sum(partially_matched, "credit_amount"),
            "unrecorded_count": len(unrecorded),
            "unrecorded_amount": _sum(unrecorded, "debit_amount"),
            "unmatched_credit_count": len(unmatched_credits),
            "unmatched_credit_amount": _sum(unmatched_credits, "credit_amount"),
            "added_count": len(added),
            "added_amount": _sum(added, "debit_amount"),
            "ignored_count": len(ignored),
            "ignored_amount": _sum(ignored, "debit_amount") + _sum(ignored, "credit_amount"),
            "manual_review_count": len(manual_review),
            "manual_review_amount": _sum(manual_review, "debit_amount") + _sum(manual_review, "credit_amount"),
        },
        "matched": matched,
        "partially_matched": partially_matched,
        "unrecorded": unrecorded,
        "unmatched_credits": unmatched_credits,
        "added": added,
        "ignored": ignored,
        "manual_review": manual_review,
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
            "Type": (txn.get("txn_type") or "").upper(),
            "Narration": txn.get("narration", ""),
            "Debit (₹)": txn.get("debit_amount", 0),
            "Credit (₹)": txn.get("credit_amount", 0),
            "Suggested Category / Source": txn.get("suggested_category") or txn.get("credit_source_hint") or "",
            "Status": (txn.get("recon_status") or txn.get("match_status") or "").upper(),
            "Match Method": txn.get("match_method", "") or "",
            "Reference": txn.get("reference_number", ""),
            "Ignore Reason": txn.get("ignore_reason", "") or "",
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

# ── Phase 3: AI Categorization (Claude via Emergent LLM Key) ────────────
# Auto-classifies unmatched bank narrations against the Category Master.
# Used to bulk-tag IDFC / MGT statements before user converts to expenses.

class AICategorizeRequest(BaseModel):
    upload_id: str
    token: str
    transaction_ids: Optional[List[str]] = None  # if None, all unmatched debits


@router.post("/ai-categorize")
async def ai_categorize_transactions(req: AICategorizeRequest):
    """Use Claude to suggest expense categories for unmatched bank debits.
    The LLM is constrained to pick from the active Category Master so its
    output is always valid for downstream conversion to expense rows.
    """
    import os
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}

    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        return {"detail": "EMERGENT_LLM_KEY not configured", "success": False}

    # Pull active category master
    heads = await db.expense_heads.find(
        {"is_active": {"$ne": False}}, {"_id": 0, "name": 1}
    ).to_list(200)
    cats = [h["name"] for h in heads if h.get("name")]
    if not cats:
        return {"detail": "No categories configured in Category Master", "success": False}

    # Pull transactions to categorize — only unmatched debits / manual review
    query: dict = {"upload_id": req.upload_id,
                   "match_status": {"$in": ["unrecorded", "manual_review"]},
                   "txn_type": "debit"}
    if req.transaction_ids:
        query["transaction_id"] = {"$in": req.transaction_ids}

    txns = await db.bank_transactions.find(query, {"_id": 0}).to_list(500)
    if not txns:
        return {"success": True, "categorized": 0, "message": "No transactions need AI categorization"}

    # Build batched prompt — Claude classifies each narration against the
    # constrained category list. Returns JSON for safe parsing.
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        return {"detail": "emergentintegrations not installed", "success": False}

    items = [{"id": t["transaction_id"],
              "narration": t.get("narration", "")[:200],
              "amount": t.get("debit_amount", 0)} for t in txns]

    system_msg = (
        "You are a financial categorization assistant for a restaurant franchise "
        "in India. Given a bank transaction narration, pick the SINGLE most likely "
        "expense category from the provided master list. Return strictly valid JSON: "
        '{"assignments": [{"id": "...", "category": "...", "confidence": 0.0-1.0, "reasoning": "short"}]}\n'
        f"Allowed categories (pick EXACTLY one per narration, case-sensitive): {cats}\n"
        "If a narration is clearly NOT an operating expense (transfer between own accounts, "
        "loan disbursement, capital injection), use category 'MISCELLANEOUS' and lower the "
        "confidence to 0.3 with the reasoning explaining why."
    )
    user_msg = (
        "Categorize these bank debits. Return ONLY the JSON, no preamble.\n\n"
        f"{items}"
    )

    session_id = f"bank-recon-{req.upload_id}"
    try:
        chat = (
            LlmChat(api_key=api_key, session_id=session_id, system_message=system_msg)
            .with_model("anthropic", "claude-sonnet-4-5-20250929")
        )
        reply = await chat.send_message(UserMessage(text=user_msg))
        raw = reply.strip() if isinstance(reply, str) else str(reply)
    except Exception as e:
        logger.error(f"Claude categorization failed: {e}")
        return {"detail": f"AI categorization failed: {str(e)[:200]}", "success": False}

    # Parse JSON robustly — strip markdown fences if present
    import json
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        assignments = parsed.get("assignments", [])
    except Exception:
        # Fallback: extract first JSON object substring
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            return {"detail": "Could not parse AI response", "success": False, "raw": raw[:500]}
        try:
            parsed = json.loads(m.group(0))
            assignments = parsed.get("assignments", [])
        except Exception:
            return {"detail": "AI returned malformed JSON", "success": False, "raw": raw[:500]}

    # Validate categories against master, persist as suggestions
    cat_set = set(cats)
    actor = session.get("name", session.get("mobile", ""))
    now_iso = datetime.now(timezone.utc).isoformat()
    updated = 0
    for a in assignments:
        tid = a.get("id")
        cat = a.get("category", "")
        if not tid or cat not in cat_set:
            continue
        conf = float(a.get("confidence", 0) or 0)
        reasoning = (a.get("reasoning") or "")[:300]
        await db.bank_transactions.update_one(
            {"transaction_id": tid, "upload_id": req.upload_id},
            {"$set": {
                "ai_suggested_category": cat,
                "ai_confidence": conf,
                "ai_reasoning": reasoning,
                "ai_categorized_at": now_iso,
                "ai_categorized_by": actor,
            }}
        )
        updated += 1

    # Audit log
    await db.expense_reconciliation_log.insert_one({
        "upload_id": req.upload_id,
        "action": "ai_categorize_batch",
        "categorized_count": updated,
        "total_requested": len(items),
        "action_taken_by": actor,
        "timestamp": now_iso,
    })

    return {
        "success": True,
        "categorized": updated,
        "total": len(items),
        "message": f"Claude classified {updated} of {len(items)} transactions",
    }


# ── Phase 3: Auto-Convert AI categorization to Expense rows ─────────────

class AutoConvertRequest(BaseModel):
    upload_id: str
    token: str
    min_confidence: float = 0.7  # auto-convert only when AI is confident
    transaction_ids: Optional[List[str]] = None
    payment_mode: str = "Bank Transfer"


@router.post("/auto-convert")
async def auto_convert_to_expenses(req: AutoConvertRequest):
    """Convert AI-categorized bank debits into expense rows in bulk.
    Skips duplicates (same center+date+amount already booked) to avoid
    double-entry when the user is re-uploading a previously processed file.
    """
    session = await _get_session(req.token)
    if not session:
        return {"detail": "Authentication required"}

    query: dict = {
        "upload_id": req.upload_id,
        "match_status": {"$in": ["unrecorded", "manual_review"]},
        "txn_type": "debit",
        "ai_suggested_category": {"$exists": True, "$nin": [None, ""]},
        "ai_confidence": {"$gte": req.min_confidence},
    }
    if req.transaction_ids:
        query["transaction_id"] = {"$in": req.transaction_ids}

    txns = await db.bank_transactions.find(query, {"_id": 0}).to_list(500)
    if not txns:
        return {"success": True, "converted": 0, "skipped_dupes": 0,
                "message": "No AI-categorized transactions met the confidence threshold"}

    actor = session.get("name", session.get("mobile", ""))
    now_iso = datetime.now(timezone.utc).isoformat()
    converted = 0
    skipped_dupes = 0
    errors: List[str] = []

    for txn in txns:
        try:
            cat = txn.get("ai_suggested_category")
            # Duplicate guard — same center + date + amount already booked?
            dup = await db.expenses.find_one({
                "center": txn["center"],
                "date": txn["transaction_date"],
                "amount": txn["debit_amount"],
            })
            if dup:
                skipped_dupes += 1
                await db.bank_transactions.update_one(
                    {"transaction_id": txn["transaction_id"], "upload_id": req.upload_id},
                    {"$set": {"match_status": "matched", "recon_status": "matched",
                              "matched_expense": {
                                  "description": dup.get("description", ""),
                                  "expense_type": dup.get("expense_type", ""),
                                  "payment_mode": dup.get("payment_mode", ""),
                                  "date": dup.get("date", ""),
                                  "amount": dup.get("amount", 0),
                              },
                              "match_method": "auto_convert_dedupe"}}
                )
                continue

            expense_id = str(uuid.uuid4())[:16]
            await db.expenses.insert_one({
                "expense_id": expense_id,
                "center": txn["center"],
                "date": txn["transaction_date"],
                "description": txn.get("narration", "")[:300],
                "amount": txn["debit_amount"],
                "expense_type": cat,
                "payment_mode": req.payment_mode,
                "reference_number": txn.get("reference_number", ""),
                "source": "bank_reconciliation_ai",
                "ai_confidence": txn.get("ai_confidence"),
                "ai_reasoning": txn.get("ai_reasoning"),
                "bank_upload_id": req.upload_id,
                "bank_transaction_id": txn["transaction_id"],
                "created_by": actor,
                "created_at": now_iso,
            })
            await db.bank_transactions.update_one(
                {"transaction_id": txn["transaction_id"], "upload_id": req.upload_id},
                {"$set": {"match_status": "added", "added_expense_id": expense_id,
                          "auto_converted": True}}
            )
            await db.expense_reconciliation_log.insert_one({
                "upload_id": req.upload_id,
                "bank_transaction_id": txn["transaction_id"],
                "matched_expense_id": expense_id,
                "ai_suggested_category": cat,
                "ai_confidence": txn.get("ai_confidence"),
                "final_category": cat,
                "action": "ai_auto_convert",
                "reconciliation_status": "added",
                "action_taken_by": actor,
                "timestamp": now_iso,
            })
            converted += 1
        except Exception as e:
            errors.append(f"{txn.get('transaction_id', '')}: {str(e)[:100]}")

    return {
        "success": True,
        "converted": converted,
        "skipped_dupes": skipped_dupes,
        "errors": errors[:20],
        "message": (f"Converted {converted} AI-tagged transactions to expenses; "
                    f"skipped {skipped_dupes} duplicate(s).")
    }

