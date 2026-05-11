# =======================================
# Ledgers Routes — CA-Ready Books of Accounts
# =======================================
# Produces monthly / FY ledgers as per Indian accounting conventions for each center.
# All ledgers are computed from existing collections (daily_sales, expenses,
# monthly_commissions, loan_entries, employees, other_income, wc_topups, bank_transactions).
# No double-entry; these are source-registers for the CA to use.

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import logging
import calendar

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ledgers", tags=["Ledgers"])

# injected from server.py
db = None
verify_token = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

# =========================================================
# Access control
# =========================================================
ACCOUNTS_ROLES = {"accounts", "account", "cfo", "finance"}

def _has_ledger_access(session: dict) -> bool:
    """Super Admin / Admin / Accounts role can access internal ledgers."""
    if not session:
        return False
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    role_key = (session.get("role_key") or "").lower()
    if role_key in ACCOUNTS_ROLES:
        return True
    # roles can be either a dict (key→bool, current schema) or a legacy list of
    # dicts. Handle both shapes defensively — the franchise-owner sessions store
    # a dict, which used to throw AttributeError ('str' object has no attribute 'get').
    roles = session.get("roles")
    if isinstance(roles, dict):
        if roles.get("accounting") or roles.get("accounts") or roles.get("finance"):
            return True
    elif isinstance(roles, list):
        for r in roles:
            if isinstance(r, dict):
                if (r.get("key") or r.get("name") or "").lower() in ACCOUNTS_ROLES:
                    return True
            elif isinstance(r, str):
                if r.lower() in ACCOUNTS_ROLES:
                    return True
    return False

def _is_franchise_owner(session: dict) -> bool:
    role_key = (session.get("role_key") or "").lower()
    return role_key == "franchise_owner"

def _check(session):
    if not session:
        raise HTTPException(401, "Invalid or expired token")

# =========================================================
# Shared helpers
# =========================================================
def _fy_range(fy_start_year: int) -> Tuple[str, str, List[str]]:
    """Given FY start year (e.g. 2025 → 1-Apr-2025 to 31-Mar-2026) return (start, end_exclusive, list of YYYY-MM)."""
    start = f"{fy_start_year}-04-01"
    end_excl = f"{fy_start_year+1}-04-01"
    months = []
    for m in range(4, 13):
        months.append(f"{fy_start_year}-{m:02d}")
    for m in range(1, 4):
        months.append(f"{fy_start_year+1}-{m:02d}")
    return start, end_excl, months

def _month_range(month_str: str) -> Tuple[str, str]:
    """'2026-04' → ('2026-04-01', '2026-05-01')"""
    y, m = [int(x) for x in month_str.split("-")]
    start = f"{y:04d}-{m:02d}-01"
    if m == 12:
        end = f"{y+1:04d}-01-01"
    else:
        end = f"{y:04d}-{m+1:02d}-01"
    return start, end

def _inr(x) -> str:
    try:
        return f"{float(x or 0):,.2f}"
    except Exception:
        return "0.00"

# Requests
class LedgerRequest(BaseModel):
    token: str
    center: str
    period_type: str  # 'month' | 'fy'
    month: Optional[str] = None       # '2026-04' when period_type='month'
    fy_start_year: Optional[int] = None  # 2025 (= FY2025-26) when period_type='fy'
    fmt: Optional[str] = "pdf"         # 'pdf' | 'excel' | 'json'

class BundleRequest(BaseModel):
    token: str
    center: str
    period_type: str
    month: Optional[str] = None
    fy_start_year: Optional[int] = None
    include_bills: Optional[bool] = True

class OwnerLedgerSendRequest(BaseModel):
    token: str
    center: str
    month: str  # which month to publish
    action: str  # 'release' | 'hide'

# =========================================================
# Data aggregators
# =========================================================
async def _get_daily_sales(center: str, start: str, end: str) -> List[dict]:
    docs = await db.daily_sales.find(
        {"center": center, "date": {"$gte": start, "$lt": end}},
        {"_id": 0}
    ).sort("date", 1).to_list(5000)
    return docs

async def _get_expenses(center: str, start: str, end: str) -> List[dict]:
    docs = await db.expenses.find(
        {"center": center, "date": {"$gte": start, "$lt": end}},
        {"_id": 0}
    ).sort("date", 1).to_list(10000)
    return docs

async def _get_commissions(center: str, months: List[str]) -> List[dict]:
    docs = await db.monthly_commissions.find(
        {"center": center, "month": {"$in": months}},
        {"_id": 0}
    ).to_list(5000)
    return docs

async def _get_loan_entries(center: str, months: List[str]) -> List[dict]:
    # Fetch all loan entries for this center; filter by loan_date month
    docs = await db.loan_entries.find(
        {"center": center}, {"_id": 0}
    ).sort("loan_date", 1).to_list(5000)
    months_set = set(months)
    out = []
    for d in docs:
        d_month = (d.get("loan_date") or "")[:7]
        if d_month in months_set:
            out.append(d)
        else:
            # also include if any repayment falls in range
            for rp in (d.get("repayments") or []):
                if (rp.get("repayment_date") or "")[:7] in months_set:
                    out.append(d)
                    break
    return out

async def _get_other_income(center: str, months: List[str]) -> List[dict]:
    docs = await db.other_income.find(
        {"center": center, "month": {"$in": months}}, {"_id": 0}
    ).to_list(2000)
    return docs

async def _get_wc_topups(center: str, months: List[str]) -> List[dict]:
    docs = await db.wc_topups.find(
        {"center": center}, {"_id": 0}
    ).to_list(500)
    months_set = set(months)
    return [d for d in docs if (d.get("month") or d.get("date", "")[:7]) in months_set]

async def _get_employees(center: str) -> List[dict]:
    docs = await db.employees.find(
        {"center": center, "is_deleted": {"$ne": True}, "active": {"$ne": False}}, {"_id": 0}
    ).to_list(1000)
    return docs

async def _get_bank_transactions(center: str, start: str, end: str) -> List[dict]:
    try:
        docs = await db.bank_transactions.find(
            {"center": center, "date": {"$gte": start, "$lt": end}}, {"_id": 0}
        ).sort("date", 1).to_list(10000)
    except Exception:
        docs = []
    return docs

# =========================================================
# Ledger builders (return dict with rows + totals)
# =========================================================
async def build_sales_register(center: str, start: str, end: str) -> Dict[str, Any]:
    from utils.gst import gst_rate_for, carve_inclusive_gst
    sales = await _get_daily_sales(center, start, end)
    rate = gst_rate_for(None, center)
    rows = []
    tot = {"direct": 0, "swiggy": 0, "zomato": 0, "doordash": 0, "card": 0, "upi": 0, "online_other": 0, "cash": 0, "total": 0, "gst": 0}
    for s in sales:
        direct = (s.get("sale_pbm") or 0) + (s.get("sale_other") or 0)
        swiggy = s.get("swiggy") or 0
        zomato = s.get("zomato") or 0
        doordash = s.get("doordash") or 0
        card = s.get("card_idfc") or 0
        upi = s.get("bharat_pay") or 0
        online_other = s.get("online_other") or 0
        cash = s.get("total_cash_sale") or 0
        total = s.get("total_sale") or (direct + swiggy + zomato + doordash + card + upi + online_other + cash)
        # Recompute GST from eligible (single source of truth, inclusive basis)
        eligible = max(0.0, float(total) - float(swiggy) - float(zomato) - float(doordash))
        gst = carve_inclusive_gst(eligible, rate)
        rows.append({
            "date": s.get("date"), "direct": direct, "swiggy": swiggy, "zomato": zomato,
            "doordash": doordash, "card": card, "upi": upi, "online_other": online_other,
            "cash": cash, "total": total, "gst": gst
        })
        for k in tot: tot[k] += locals().get(k, 0) if k in ("direct", "swiggy", "zomato", "doordash", "card", "upi", "online_other", "cash", "total", "gst") else 0
    return {"rows": rows, "totals": tot}

async def build_expense_register(center: str, start: str, end: str) -> Dict[str, Any]:
    expenses = await _get_expenses(center, start, end)
    rows = []
    by_cat: Dict[str, float] = {}
    by_mode: Dict[str, float] = {}
    total = 0.0
    input_gst_total = 0.0
    taxable_base_total = 0.0
    for e in expenses:
        cat = e.get("expense_type") or "Other"
        mode = e.get("payment_mode") or "UNKNOWN"
        amt = float(e.get("amount") or 0)
        gst_rate = float(e.get("gst_rate") or 0)
        gst_amt = float(e.get("gst_amount") or 0)
        # Auto-derive for legacy rows where rate is set but amount is 0
        if gst_rate > 0 and not gst_amt:
            gst_amt = round(amt * gst_rate / (100 + gst_rate), 2)
        taxable = max(0, amt - gst_amt)
        # attachment marker
        has_att = bool(e.get("attachments")) or bool(e.get("invoice_group_id"))
        rows.append({
            "date": e.get("date"),
            "description": e.get("description") or "",
            "category": cat,
            "payment_mode": mode,
            "vendor_name": e.get("vendor_name") or "",
            "vendor_gstin": e.get("vendor_gstin") or "",
            "taxable_value": taxable,
            "gst_rate": gst_rate,
            "gst_amount": gst_amt,
            "amount": amt,
            "bill_attached": has_att,
        })
        by_cat[cat] = by_cat.get(cat, 0) + amt
        by_mode[mode] = by_mode.get(mode, 0) + amt
        total += amt
        input_gst_total += gst_amt
        taxable_base_total += taxable
    return {
        "rows": rows,
        "by_category": by_cat,
        "by_mode": by_mode,
        "total": total,
        "input_gst_total": round(input_gst_total, 2),
        "taxable_base_total": round(taxable_base_total, 2),
    }

async def build_cash_book(center: str, start: str, end: str) -> Dict[str, Any]:
    sales = await _get_daily_sales(center, start, end)
    rows = []
    open_bal = None
    for s in sales:
        op = s.get("petty_cash_opening") or 0
        receipts = s.get("cash_receipts") or 0
        cash_sale = s.get("total_cash_sale") or 0
        cash_exp = s.get("cash_expense") or 0
        deposited = s.get("deposited_in_bank") or 0
        closing = s.get("petty_cash_closing") if s.get("petty_cash_closing") is not None else (op + receipts + cash_sale - cash_exp - deposited)
        if open_bal is None:
            open_bal = op
        rows.append({
            "date": s.get("date"),
            "opening": op,
            "cash_sale": cash_sale,
            "cash_receipts": receipts,
            "cash_expenses": cash_exp,
            "deposited_in_bank": deposited,
            "closing": closing,
        })
    totals = {
        "opening": open_bal or 0,
        "cash_sale": sum(r["cash_sale"] for r in rows),
        "cash_receipts": sum(r["cash_receipts"] for r in rows),
        "cash_expenses": sum(r["cash_expenses"] for r in rows),
        "deposited_in_bank": sum(r["deposited_in_bank"] for r in rows),
        "closing": rows[-1]["closing"] if rows else 0,
    }
    return {"rows": rows, "totals": totals}

async def build_bank_book(center: str, start: str, end: str) -> Dict[str, Any]:
    # Use bank_transactions collection if populated; else derive from daily_sales deposits.
    rows = []
    txns = await _get_bank_transactions(center, start, end)
    if txns:
        bal = 0.0
        for t in txns:
            credit = float(t.get("credit") or (t.get("amount") if t.get("direction") in ("in", "credit") else 0) or 0)
            debit = float(t.get("debit") or (t.get("amount") if t.get("direction") in ("out", "debit") else 0) or 0)
            bal += credit - debit
            rows.append({
                "date": t.get("date"),
                "particulars": t.get("narration") or t.get("description") or t.get("source", ""),
                "credit": credit,
                "debit": debit,
                "balance": bal,
            })
    else:
        # Fallback: derive from daily_sales (deposits as credits)
        sales = await _get_daily_sales(center, start, end)
        bal = 0.0
        for s in sales:
            dep = s.get("deposited_in_bank") or 0
            wd = s.get("cash_receipts") or 0  # cash withdrawn from bank
            if dep:
                bal += dep
                rows.append({"date": s.get("date"), "particulars": "Cash deposit", "credit": dep, "debit": 0, "balance": bal})
            if wd:
                bal -= wd
                rows.append({"date": s.get("date"), "particulars": "Cash withdrawal (petty cash)", "credit": 0, "debit": wd, "balance": bal})
    totals = {
        "credit": sum(r["credit"] for r in rows),
        "debit": sum(r["debit"] for r in rows),
        "closing": rows[-1]["balance"] if rows else 0,
    }
    return {"rows": rows, "totals": totals}

async def build_commission_ledger(center: str, months: List[str]) -> Dict[str, Any]:
    comms = await _get_commissions(center, months)
    by_platform: Dict[str, Dict[str, float]] = {}
    rows = []
    for c in comms:
        plat = (c.get("platform") or "").lower() or "unknown"
        gross = float(c.get("gross_amount") or 0)
        gst_ded = float(c.get("gst_tax_deductions") or 0)
        oth_ded = float(c.get("other_deductions") or 0)
        comm_total = gst_ded + oth_ded or float(c.get("commission_amount") or 0)
        net = float(c.get("net_amount") or (gross - comm_total))
        rows.append({
            "month": c.get("month"), "platform": plat, "gross": gross,
            "gst_deduction": gst_ded, "other_deduction": oth_ded,
            "commission": comm_total, "net": net,
        })
        p = by_platform.setdefault(plat, {"gross": 0, "gst_deduction": 0, "other_deduction": 0, "commission": 0, "net": 0})
        p["gross"] += gross
        p["gst_deduction"] += gst_ded
        p["other_deduction"] += oth_ded
        p["commission"] += comm_total
        p["net"] += net
    totals = {"gross": sum(v["gross"] for v in by_platform.values()),
              "commission": sum(v["commission"] for v in by_platform.values()),
              "net": sum(v["net"] for v in by_platform.values())}
    return {"rows": sorted(rows, key=lambda r: (r["month"], r["platform"])), "by_platform": by_platform, "totals": totals}

async def build_loan_ledger(center: str, months: List[str]) -> Dict[str, Any]:
    loans = await _get_loan_entries(center, months)
    # Group by counterparty
    parties: Dict[str, Dict[str, Any]] = {}
    for l in loans:
        is_given = l.get("loan_type") == "given"
        party = (l.get("target_center") if is_given else (l.get("source_center") or "HQ")) or "HQ"
        label = (l.get("target_center_name") if is_given else l.get("source_center_name")) or ("HQ / External" if not is_given else "Other")
        p = parties.setdefault(party, {"label": label, "rows": [], "total_principal": 0, "total_repaid": 0, "outstanding": 0, "direction": "given" if is_given else "taken"})
        # Loan principal row
        p["rows"].append({
            "date": l.get("loan_date"),
            "particulars": f"{'Given' if is_given else 'Taken'} — {l.get('reason') or l.get('loan_id')}",
            "debit": l.get("amount") if is_given else 0,
            "credit": l.get("amount") if not is_given else 0,
        })
        p["total_principal"] += l.get("amount") or 0
        # Repayment rows
        for rp in (l.get("repayments") or []):
            amt = rp.get("amount") or 0
            p["rows"].append({
                "date": rp.get("repayment_date"),
                "particulars": f"Repayment — {l.get('loan_id')}",
                "debit": 0 if is_given else amt,
                "credit": amt if is_given else 0,
            })
            p["total_repaid"] += amt
        p["outstanding"] = max(0, p["total_principal"] - p["total_repaid"])
    # Sort rows & compute running balance per party
    for key, p in parties.items():
        p["rows"].sort(key=lambda r: r["date"] or "")
        bal = 0.0
        for r in p["rows"]:
            bal += (r["credit"] or 0) - (r["debit"] or 0)
            r["balance"] = bal
    totals = {
        "principal": sum(p["total_principal"] for p in parties.values()),
        "repaid": sum(p["total_repaid"] for p in parties.values()),
        "outstanding": sum(p["outstanding"] for p in parties.values()),
    }
    return {"parties": parties, "totals": totals}

async def build_payroll_register(center: str, months: List[str]) -> Dict[str, Any]:
    employees = await _get_employees(center)
    rows = []
    total_base = 0.0
    total_current = 0.0
    for e in employees:
        # Field names in DB are camelCase: salaryBase / currentSalary
        base = float(e.get("salaryBase") or e.get("base_salary") or e.get("basic_salary") or 0)
        current = float(e.get("currentSalary") or e.get("current_salary") or e.get("salary") or base)
        rows.append({
            "employee_id": e.get("employee_id") or e.get("emp_id") or "",
            "name": e.get("name") or "",
            "designation": e.get("designation") or e.get("role") or "",
            "doj": e.get("dateOfJoining") or e.get("date_of_joining") or e.get("doj") or "",
            "base_salary": base,
            "current_salary": current,
            "bank_name": e.get("bankName") or e.get("bank_name") or "",
            "account_no": e.get("beneAccNo") or e.get("account_number") or e.get("bank_account") or "",
            "ifsc": e.get("ifsc") or "",
            "pan": e.get("pan") or e.get("PAN") or "",
            "aadhaar": e.get("aadhaar") or e.get("aadhar") or "",
        })
        total_base += base
        total_current += current
    # Monthly total is current_salary × number of months
    months_n = len(months)
    return {
        "rows": rows,
        "months": months,
        "totals": {
            "employee_count": len(rows),
            "monthly_base": total_base,
            "monthly_current": total_current,
            "period_current": total_current * months_n,
        }
    }

async def build_gst_summary(center: str, start: str, end: str, months: List[str]) -> Dict[str, Any]:
    # Output GST: use shared utility (single source of truth, INCLUSIVE on eligible sales)
    from utils.gst import compute_gst_from_rows
    sales = await _get_daily_sales(center, start, end)
    _gst_calc = compute_gst_from_rows(sales, country=None, center=center)
    output_gst = _gst_calc["gst_amount"]
    taxable = _gst_calc["eligible_base"] - output_gst  # taxable value (ex-GST)
    # Input GST (ITC) from expenses tagged with gst_rate / gst_amount
    exp_data = await build_expense_register(center, start, end)
    input_gst = exp_data.get("input_gst_total", 0.0)
    itc_taxable = exp_data.get("taxable_base_total", 0.0)
    # Commission GST (input — reverse charge on aggregator commissions may apply; we show as info)
    comms = await _get_commissions(center, months)
    commission_gst = sum(float(c.get("gst_tax_deductions") or 0) for c in comms)
    net_liability = round(max(0, output_gst - input_gst), 2)
    return {
        "output_gst": round(output_gst, 2),
        "taxable_value": round(taxable, 2),
        "eligible_base": round(_gst_calc["eligible_base"], 2),
        "aggregator_sale": round(_gst_calc["aggregator_sale"], 2),
        "total_sale": round(_gst_calc["total_sale"], 2),
        "input_gst": round(input_gst, 2),
        "itc_taxable_value": round(itc_taxable, 2),
        "commission_gst_charged": round(commission_gst, 2),
        "net_liability": net_liability,
        "note": "Output GST = Eligible − Eligible/(1+rate). Eligible = Total Sale − Swiggy − Zomato − DoorDash. Input GST (ITC) sourced from tagged expenses. Verify with your CA."
    }

async def build_monthly_pnl(center: str, months: List[str]) -> Dict[str, Any]:
    from utils.gst import compute_gst_from_rows
    from_months = sorted(months)
    rows = []
    for m in from_months:
        st, en = _month_range(m)
        sales = await _get_daily_sales(center, st, en)
        expenses = await _get_expenses(center, st, en)
        total_sale = sum((s.get("total_sale") or 0) for s in sales)
        # GST via single source of truth (inclusive, eligible-base)
        gst = compute_gst_from_rows(sales, country=None, center=center)["gst_amount"]
        sales_ex_gst = total_sale - gst
        total_exp = sum((e.get("amount") or 0) for e in expenses)
        comms = await _get_commissions(center, [m])
        comm_total = sum((float(c.get("gst_tax_deductions") or 0) + float(c.get("other_deductions") or 0)) or float(c.get("commission_amount") or 0) for c in comms)
        pbt = sales_ex_gst - total_exp - comm_total
        rows.append({
            "month": m,
            "sales_gross": total_sale,
            "gst": gst,
            "sales_ex_gst": sales_ex_gst,
            "expenses": total_exp,
            "commissions": comm_total,
            "pbt": pbt,
        })
    totals = {k: sum(r[k] for r in rows) for k in ("sales_gross", "gst", "sales_ex_gst", "expenses", "commissions", "pbt")}
    return {"rows": rows, "totals": totals}

async def build_franchise_owner_ledger(center: str, months: List[str]) -> Dict[str, Any]:
    """Running running-account statement between Franchise Owner & HQ, month-wise.
    Credit = amount owed by HQ to Franchise. Debit = amount owed by Franchise to HQ.
    """
    rows: List[dict] = []
    # Resolve franchise: centers.franchise_code → franchises.franchise_code
    center_doc = await db.centers.find_one({"code": center}, {"_id": 0})
    country = (center_doc.get("country") if center_doc else None) or "India"
    franchise = None
    if center_doc and center_doc.get("franchise_code"):
        franchise = await db.franchises.find_one({"franchise_code": center_doc["franchise_code"]}, {"_id": 0})
    if not franchise:
        # Legacy fallback patterns
        franchise = await db.franchises.find_one({"centers_mapped": center}, {"_id": 0}) or \
                    await db.franchises.find_one({"center": center}, {"_id": 0})
    rev_pct = 0.0
    mg = 0.0
    if franchise:
        rev_pct = float(franchise.get("revenue_share_percentage") or franchise.get("revenue_share_percent") or franchise.get("revenue_share") or 0)
        mg = float(franchise.get("monthly_guarantee") or franchise.get("mg") or franchise.get("minimum_guarantee") or 0)
    # Overseas centers do NOT have an MG — they use a fixed 80/20 profit share
    # with a 5% MFPL royalty accrued separately. Set rev_pct=80, mg=0.
    from utils.overseas_share import is_overseas as _is_overseas, MFPL_ROYALTY_PCT, MFPL_ACCRUAL_START_MONTH
    _overseas = _is_overseas(country)
    if _overseas:
        rev_pct = 80.0
        mg = 0.0

    running = 0.0
    is_first_month = True
    total_rev_share = 0.0  # accumulated for Final Payout block
    total_mg_topup = 0.0
    total_mfpl_accrued = 0.0  # overseas-only: cumulative MFPL royalty
    # Accumulators for the "Eligible Rev Share Base" breakout in the PDF.
    period_total_sales = 0.0
    period_total_commission_base = 0.0  # commission excl. commission GST
    period_total_commission_gst = 0.0
    period_total_gst_on_sales = 0.0
    for m in sorted(months):
        st, en = _month_range(m)
        sales = await _get_daily_sales(center, st, en)

        # ── Use the SAME formula as PIB / MIS Dashboard / Center Accounts ──
        # Single source of truth = utils.gst.compute_net_revenue:
        #   India     : Net Rev = Total Sale − Commissions − GST
        #   Outside-IN: Net Rev = Total Sale − GST − Commissions × (1 + rate)
        # Revenue Share = Net Revenue × rev_pct%
        from utils.gst import compute_gst_from_rows, compute_net_revenue
        total_sales = sum((s.get("total_sale") or 0) for s in sales)
        gst_calc = compute_gst_from_rows(sales, country=country, center=center)
        gst_amount = float(gst_calc.get("gst_amount") or 0)

        comms = await _get_commissions(center, [m])
        comm_total = sum(
            (float(c.get("gst_tax_deductions") or 0) + float(c.get("other_deductions") or 0))
            or float(c.get("commission_amount") or 0)
            for c in comms
        )
        # Track commission GST separately so the PDF can show the explicit
        # "Eligible Rev Share Base = Sales − Comm − Comm GST − GST" breakout.
        comm_gst_only = sum(float(c.get("gst_tax_deductions") or 0) for c in comms)
        period_total_sales += float(total_sales or 0)
        period_total_commission_base += float(comm_total) - float(comm_gst_only)
        period_total_commission_gst += float(comm_gst_only)
        period_total_gst_on_sales += float(gst_amount or 0)

        net_revenue = max(0.0, compute_net_revenue(total_sales, comm_total, gst_amount, 0, country))
        if _overseas:
            # Overseas: Eligible Profit = Sales − GST − Commission − CommGST − Expenses
            # (commission already includes CommGST for AU). Share Owner = 80% × Eligible Profit.
            exp_rows = await _get_expenses(center, st, en)
            month_expenses = sum(float(e.get("amount") or 0) for e in exp_rows)
            eligible_profit_local = max(0.0, total_sales - gst_amount - comm_total - month_expenses)
            rev_share = round(eligible_profit_local * 80.0 / 100.0, 2)
            mg_delta = 0.0
            # 5% MFPL royalty on Net Sales (Sales − GST) — only from FY-start
            # (MFPL_ACCRUAL_START_MONTH). Months before this do not accrue.
            if m >= MFPL_ACCRUAL_START_MONTH:
                mfpl_accrued_month = round(max(0.0, total_sales - gst_amount) * MFPL_ROYALTY_PCT / 100.0, 2)
            else:
                mfpl_accrued_month = 0.0
        else:
            rev_share = round(net_revenue * rev_pct / 100, 2)
            mg_delta = max(0, mg - rev_share)  # HQ owes franchisee extra if rev_share < MG
            mfpl_accrued_month = 0.0
        total_rev_share += rev_share
        total_mg_topup += mg_delta
        total_mfpl_accrued += mfpl_accrued_month

        # Loans taken / given / repayments in this month
        loans = await _get_loan_entries(center, [m])
        loan_taken = sum(l.get("amount") or 0 for l in loans if l.get("loan_type") != "given" and (l.get("loan_date") or "")[:7] == m)
        loan_given = sum(l.get("amount") or 0 for l in loans if l.get("loan_type") == "given" and (l.get("loan_date") or "")[:7] == m)
        repayments_by_franchise = 0.0  # money franchise paid back on loans taken
        repayments_to_franchise = 0.0  # repayments received on loans given
        for l in loans:
            for rp in (l.get("repayments") or []):
                if (rp.get("repayment_date") or "")[:7] == m:
                    if l.get("loan_type") == "given":
                        repayments_to_franchise += rp.get("amount") or 0
                    else:
                        repayments_by_franchise += rp.get("amount") or 0

        # WC Topups (HQ to center = credit to franchise)
        topups = await _get_wc_topups(center, [m])
        topup_total = sum(float(t.get("amount") or 0) for t in topups if (t.get("month") or t.get("date", "")[:7]) == m)

        # Other income
        oi = await _get_other_income(center, [m])
        oi_total = sum(float(o.get("amount") or 0) for o in oi)

        # Build ledger entries for the month
        # Only show "Opening Balance" once at the very start of the period
        entries: List[Tuple[Any, ...]] = []
        if is_first_month:
            entries.append(("Opening Balance (HQ ↔ Franchise)", 0, 0, running, True))
            is_first_month = False
        # GST grossup on Revenue Share — what the franchise actually invoices
        # (Final Payout = Rev Share × 1.18 for India, ×1.10 for Australia).
        # This makes the running balance match the Final Payout block in the
        # PDF and what every other dashboard shows. Skipped when MG > Rev Share
        # because in that case MG (a fixed sum, no GST grossup on top) is paid.
        if (country or "India").lower() == "india":
            share_gst_rate = 18.0
        else:
            share_gst_rate = 10.0
        share_gst_amount = round(rev_share * share_gst_rate / 100, 2) if rev_share else 0.0

        entries += [
            (f"{m} — {'Profit Share' if _overseas else 'Revenue Share'} payable ({rev_pct:g}%)", rev_share, 0, None, False) if rev_share else None,
            (f"{m} — GST on {'Profit' if _overseas else 'Revenue'} Share @ {share_gst_rate:.0f}%", share_gst_amount, 0, None, False) if share_gst_amount else None,
            (f"{m} — MG top-up (HQ → Franchise)", 0, mg_delta, None, False) if (mg_delta and not _overseas) else None,
            (f"{m} — Commissions charged", comm_total, 0, None, False) if comm_total else None,
            (f"{m} — Loan taken from HQ", 0, loan_taken, None, False) if loan_taken else None,
            (f"{m} — Loan given to HQ/other", loan_given, 0, None, False) if loan_given else None,
            (f"{m} — Loan repayment by franchise", repayments_by_franchise, 0, None, False) if repayments_by_franchise else None,
            (f"{m} — Repayments received on loans given", 0, repayments_to_franchise, None, False) if repayments_to_franchise else None,
            (f"{m} — WC Top-up from HQ", 0, topup_total, None, False) if topup_total else None,
            (f"{m} — Other Income credited", 0, oi_total, None, False) if oi_total else None,
        ]
        for ent in entries:
            if not ent:
                continue
            particulars, debit, credit, balance, is_opening = ent
            if not is_opening:
                running = running + credit - debit
            rows.append({
                "date": st if is_opening else en,
                "particulars": particulars,
                "debit": debit,
                "credit": credit,
                "balance": running,
            })
    # Closing
    rows.append({
        "date": _month_range(max(months))[1],
        "particulars": "Closing Balance",
        "debit": 0, "credit": 0, "balance": running,
    })
    return {
        "rows": rows,
        "closing_balance": running,
        "total_rev_share": round(total_rev_share, 2),
        "total_mg_topup": round(total_mg_topup, 2),
        "total_mfpl_accrued": round(total_mfpl_accrued, 2),
        "overseas": _overseas,
        "country": country,
        "period_totals": {
            "total_sales": round(period_total_sales, 2),
            "total_commission_base": round(period_total_commission_base, 2),
            "total_commission_gst": round(period_total_commission_gst, 2),
            "total_gst_on_sales": round(period_total_gst_on_sales, 2),
            "eligible_rev_share_base": round(
                period_total_sales
                - period_total_commission_base
                - period_total_commission_gst
                - period_total_gst_on_sales,
                2,
            ),
        },
        "franchise": {
            "code": (franchise or {}).get("franchise_code"),
            "name": (franchise or {}).get("franchise_name"),
            "revenue_share_percent": rev_pct,
            "monthly_guarantee": mg,
        },
    }

# =========================================================
# PDF / Excel rendering
# =========================================================
def _render_pdf(title: str, subtitle: str, sections: List[Tuple[str, List[List[str]]]],
                country: Optional[str] = "India") -> bytes:
    """Generic PDF renderer: sections is [(section_title, table_data_with_header_row), ...].
    Appends Accounts CFO signature block at the end (Manaswini Foods Pvt Ltd / Purnabramha LLC Pty Ltd
    based on country)."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from utils.signature import signature_block

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1*cm, rightMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#0F172A"))
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#475569"))
    section_style = ParagraphStyle("Section", parent=styles["Heading3"], fontSize=12, textColor=colors.HexColor("#0F172A"), spaceBefore=10, spaceAfter=6)

    story = [Paragraph(title, title_style), Paragraph(subtitle, sub_style), Spacer(1, 10)]
    for sec_title, data in sections:
        if sec_title:
            story.append(Paragraph(sec_title, section_style))
        if not data or len(data) < 2:
            story.append(Paragraph("<i>No data for this section.</i>", sub_style))
            story.append(Spacer(1, 6))
            continue
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E0E7FF")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    # Authorised signatory block at the bottom (Accounts CFO)
    story.extend(signature_block(country=country, label="Authorised Signatory · Accounts"))

    doc.build(story)
    return buf.getvalue()

def _render_excel(sheets: List[Tuple[str, List[List[Any]]]]) -> bytes:
    """Each sheet = (name, rows). First row is header."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = Workbook()
    wb.remove(wb.active)
    header_fill = PatternFill("solid", fgColor="0F172A")
    header_font = Font(color="FFFFFF", bold=True)
    total_fill = PatternFill("solid", fgColor="E0E7FF")
    thin = Side(border_style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for name, rows in sheets:
        ws = wb.create_sheet(title=(name or "Sheet")[:31])
        if not rows:
            continue
        for r_idx, row in enumerate(rows, 1):
            for c_idx, val in enumerate(row, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.border = border
                if r_idx == 1:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif r_idx == len(rows) and len(rows) > 2:
                    cell.fill = total_fill
                    cell.font = Font(bold=True)
                if isinstance(val, (int, float)) and r_idx > 1:
                    cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(horizontal="right")
        # Auto width
        for col in ws.columns:
            max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)
        ws.freeze_panes = "A2"
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

# =========================================================
# Endpoints — each ledger has a fetch endpoint (PDF/Excel/JSON)
# =========================================================
async def _resolve_period(req: LedgerRequest) -> Tuple[str, str, List[str], str]:
    """Returns (start, end_exclusive, months, period_label)"""
    if req.period_type == "month":
        if not req.month:
            raise HTTPException(400, "month is required when period_type=month")
        start, end = _month_range(req.month)
        return start, end, [req.month], req.month
    elif req.period_type == "fy":
        if not req.fy_start_year:
            raise HTTPException(400, "fy_start_year is required when period_type=fy")
        start, end, months = _fy_range(int(req.fy_start_year))
        return start, end, months, f"FY{req.fy_start_year}-{req.fy_start_year+1 - 2000:02d}"
    raise HTTPException(400, "period_type must be 'month' or 'fy'")

def _sales_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Date", "Direct", "Swiggy", "Zomato", "DoorDash", "Card", "UPI", "Online Other", "Cash", "Total", "GST @5%"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["date"], _inr(r["direct"]), _inr(r["swiggy"]), _inr(r["zomato"]), _inr(r["doordash"]),
                     _inr(r["card"]), _inr(r["upi"]), _inr(r["online_other"]), _inr(r["cash"]), _inr(r["total"]), _inr(r["gst"])])
    t = data["totals"]
    rows.append(["TOTAL", _inr(t["direct"]), _inr(t["swiggy"]), _inr(t["zomato"]), _inr(t["doordash"]),
                 _inr(t["card"]), _inr(t["upi"]), _inr(t["online_other"]), _inr(t["cash"]), _inr(t["total"]), _inr(t["gst"])])
    return rows

def _sales_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Date", "Direct", "Swiggy", "Zomato", "DoorDash", "Card", "UPI", "Online Other", "Cash", "Total", "GST @5%"]]
    for r in data["rows"]:
        rows.append([r["date"], r["direct"], r["swiggy"], r["zomato"], r["doordash"], r["card"], r["upi"], r["online_other"], r["cash"], r["total"], r["gst"]])
    t = data["totals"]
    rows.append(["TOTAL", t["direct"], t["swiggy"], t["zomato"], t["doordash"], t["card"], t["upi"], t["online_other"], t["cash"], t["total"], t["gst"]])
    return rows

def _expense_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Date", "Vendor", "Description", "Category", "Mode", "Taxable", "GST %", "GST Amt", "Total", "Bill"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([
            r["date"], r.get("vendor_name") or "-", r["description"], r["category"], r["payment_mode"],
            _inr(r.get("taxable_value", 0)), f"{r.get('gst_rate', 0):.0f}%", _inr(r.get("gst_amount", 0)),
            _inr(r["amount"]), "Yes" if r["bill_attached"] else "No"
        ])
    rows.append(["", "", "", "", "TOTAL", _inr(data.get("taxable_base_total", 0)), "", _inr(data.get("input_gst_total", 0)), _inr(data["total"]), ""])
    return rows

def _expense_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Date", "Vendor", "Vendor GSTIN", "Description", "Category", "Mode", "Taxable Value", "GST Rate %", "GST Amount (ITC)", "Total Amount", "Bill Attached"]]
    for r in data["rows"]:
        rows.append([
            r["date"], r.get("vendor_name") or "", r.get("vendor_gstin") or "",
            r["description"], r["category"], r["payment_mode"],
            r.get("taxable_value", 0), r.get("gst_rate", 0), r.get("gst_amount", 0),
            r["amount"], "Yes" if r["bill_attached"] else "No"
        ])
    rows.append(["", "", "", "", "", "TOTAL", data.get("taxable_base_total", 0), "", data.get("input_gst_total", 0), data["total"], ""])
    return rows

def _cash_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Date", "Opening", "Cash Sale", "Receipts (Bank→Cash)", "Cash Expenses", "Deposited to Bank", "Closing"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["date"], _inr(r["opening"]), _inr(r["cash_sale"]), _inr(r["cash_receipts"]),
                     _inr(r["cash_expenses"]), _inr(r["deposited_in_bank"]), _inr(r["closing"])])
    t = data["totals"]
    rows.append(["TOTAL", _inr(t["opening"]), _inr(t["cash_sale"]), _inr(t["cash_receipts"]),
                 _inr(t["cash_expenses"]), _inr(t["deposited_in_bank"]), _inr(t["closing"])])
    return rows

def _cash_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Date", "Opening", "Cash Sale", "Receipts (Bank→Cash)", "Cash Expenses", "Deposited to Bank", "Closing"]]
    for r in data["rows"]:
        rows.append([r["date"], r["opening"], r["cash_sale"], r["cash_receipts"], r["cash_expenses"], r["deposited_in_bank"], r["closing"]])
    t = data["totals"]
    rows.append(["TOTAL", t["opening"], t["cash_sale"], t["cash_receipts"], t["cash_expenses"], t["deposited_in_bank"], t["closing"]])
    return rows

def _bank_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Date", "Particulars", "Credit", "Debit", "Balance"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["date"], r["particulars"], _inr(r["credit"]), _inr(r["debit"]), _inr(r["balance"])])
    t = data["totals"]
    rows.append(["", "TOTAL", _inr(t["credit"]), _inr(t["debit"]), _inr(t["closing"])])
    return rows

def _bank_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Date", "Particulars", "Credit", "Debit", "Balance"]]
    for r in data["rows"]:
        rows.append([r["date"], r["particulars"], r["credit"], r["debit"], r["balance"]])
    t = data["totals"]
    rows.append(["", "TOTAL", t["credit"], t["debit"], t["closing"]])
    return rows

def _comm_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Month", "Platform", "Gross", "GST Deduction", "Other Deduction", "Total Commission", "Net"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["month"], r["platform"].upper(), _inr(r["gross"]), _inr(r["gst_deduction"]),
                     _inr(r["other_deduction"]), _inr(r["commission"]), _inr(r["net"])])
    rows.append(["", "TOTAL", _inr(data["totals"]["gross"]), "", "", _inr(data["totals"]["commission"]), _inr(data["totals"]["net"])])
    return rows

def _comm_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Month", "Platform", "Gross", "GST Deduction", "Other Deduction", "Total Commission", "Net"]]
    for r in data["rows"]:
        rows.append([r["month"], r["platform"].upper(), r["gross"], r["gst_deduction"], r["other_deduction"], r["commission"], r["net"]])
    rows.append(["", "TOTAL", data["totals"]["gross"], "", "", data["totals"]["commission"], data["totals"]["net"]])
    return rows

def _loan_to_tables(data: Dict[str, Any]) -> List[Tuple[str, List[List[str]]]]:
    sections = []
    for key, p in data["parties"].items():
        label = f"Counterparty: {p['label']} ({p['direction'].upper()})"
        hdr = ["Date", "Particulars", "Debit", "Credit", "Balance"]
        rows = [hdr]
        for r in p["rows"]:
            rows.append([r["date"] or "", r["particulars"], _inr(r["debit"]), _inr(r["credit"]), _inr(r["balance"])])
        rows.append(["", "TOTAL", _inr(p["total_repaid"] if p["direction"] == "taken" else 0),
                     _inr(p["total_principal"] if p["direction"] == "taken" else 0),
                     _inr(p["outstanding"])])
        sections.append((label, rows))
    return sections

def _loan_to_excel_sheets(data: Dict[str, Any]) -> List[Tuple[str, List[List[Any]]]]:
    sheets = []
    for key, p in data["parties"].items():
        rows = [["Date", "Particulars", "Debit", "Credit", "Balance"]]
        for r in p["rows"]:
            rows.append([r["date"] or "", r["particulars"], r["debit"], r["credit"], r["balance"]])
        rows.append(["", "TOTAL", p["total_repaid"] if p["direction"] == "taken" else 0,
                     p["total_principal"] if p["direction"] == "taken" else 0, p["outstanding"]])
        sheets.append((f"Loan-{key}", rows))
    return sheets or [("Loans", [["No loan entries in period"]])]

def _payroll_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Emp ID", "Name", "Designation", "DoJ", "Base Salary", "Current Salary", "Bank", "A/c No", "IFSC", "PAN"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["employee_id"], r["name"], r["designation"], r["doj"],
                     _inr(r["base_salary"]), _inr(r["current_salary"]),
                     r["bank_name"], r["account_no"], r["ifsc"], r["pan"]])
    t = data["totals"]
    rows.append(["", f"TOTAL ({t['employee_count']} emp)", "", "", _inr(t["monthly_base"]), _inr(t["monthly_current"]), "", "", "", ""])
    return rows

def _payroll_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Emp ID", "Name", "Designation", "DoJ", "Base Salary", "Current Salary", "Bank", "A/c No", "IFSC", "PAN"]]
    for r in data["rows"]:
        rows.append([r["employee_id"], r["name"], r["designation"], r["doj"],
                     r["base_salary"], r["current_salary"], r["bank_name"], r["account_no"], r["ifsc"], r["pan"]])
    t = data["totals"]
    rows.append(["", f"TOTAL ({t['employee_count']} emp)", "", "", t["monthly_base"], t["monthly_current"], "", "", "", ""])
    return rows

def _gst_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Particulars", "Amount"]
    rows = [hdr,
            ["Taxable Value (Sales ex-GST)", _inr(data["taxable_value"])],
            ["Output GST @ 5% (Food Sales)", _inr(data["output_gst"])],
            ["", ""],
            ["ITC — Taxable Value (Expenses ex-GST)", _inr(data.get("itc_taxable_value", 0))],
            ["ITC — Input GST (from tagged expenses)", _inr(data.get("input_gst", 0))],
            ["", ""],
            ["GST on Aggregator Commissions (info)", _inr(data["commission_gst_charged"])],
            ["Net GST Liability (Output − ITC)", _inr(data["net_liability"])]]
    return rows

def _gst_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    return [["Particulars", "Amount"],
            ["Taxable Value (Sales ex-GST)", data["taxable_value"]],
            ["Output GST @ 5% (Food Sales)", data["output_gst"]],
            ["", ""],
            ["ITC — Taxable Value (Expenses ex-GST)", data.get("itc_taxable_value", 0)],
            ["ITC — Input GST (from tagged expenses)", data.get("input_gst", 0)],
            ["", ""],
            ["GST on Aggregator Commissions (info)", data["commission_gst_charged"]],
            ["Net GST Liability (Output − ITC)", data["net_liability"]]]

def _pnl_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Month", "Sales (Gross)", "GST", "Sales (Ex-GST)", "Expenses", "Commissions", "PBT"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["month"], _inr(r["sales_gross"]), _inr(r["gst"]), _inr(r["sales_ex_gst"]),
                     _inr(r["expenses"]), _inr(r["commissions"]), _inr(r["pbt"])])
    t = data["totals"]
    rows.append(["TOTAL", _inr(t["sales_gross"]), _inr(t["gst"]), _inr(t["sales_ex_gst"]), _inr(t["expenses"]), _inr(t["commissions"]), _inr(t["pbt"])])
    return rows

def _pnl_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Month", "Sales (Gross)", "GST", "Sales (Ex-GST)", "Expenses", "Commissions", "PBT"]]
    for r in data["rows"]:
        rows.append([r["month"], r["sales_gross"], r["gst"], r["sales_ex_gst"], r["expenses"], r["commissions"], r["pbt"]])
    t = data["totals"]
    rows.append(["TOTAL", t["sales_gross"], t["gst"], t["sales_ex_gst"], t["expenses"], t["commissions"], t["pbt"]])
    return rows

def _owner_ledger_to_table(data: Dict[str, Any]) -> List[List[str]]:
    hdr = ["Date", "Particulars", "Debit (Franchise→HQ)", "Credit (HQ→Franchise)", "Running Balance"]
    rows = [hdr]
    for r in data["rows"]:
        rows.append([r["date"], r["particulars"], _inr(r["debit"]), _inr(r["credit"]), _inr(r["balance"])])
    return rows

def _owner_ledger_to_excel(data: Dict[str, Any]) -> List[List[Any]]:
    rows = [["Date", "Particulars", "Debit (Franchise→HQ)", "Credit (HQ→Franchise)", "Running Balance"]]
    for r in data["rows"]:
        rows.append([r["date"], r["particulars"], r["debit"], r["credit"], r["balance"]])
    return rows

# =========================================================
# Endpoint: Get a specific ledger
# =========================================================
LEDGER_TYPES = {
    "sales": "Sales Register",
    "expenses": "Expense / Purchase Register",
    "cash": "Cash Book",
    "bank": "Bank Book",
    "commission": "Commission / Aggregator Ledger",
    "loans": "Loan / Counterparty Ledger",
    "payroll": "Payroll Register",
    "gst": "GST Summary",
    "pnl": "Profit & Loss Statement",
    "owner": "Franchise Owner Ledger",
}

@router.post("/get")
async def get_ledger(req: LedgerRequest):
    session = verify_token(req.token)
    _check(session)
    ledger = (req.fmt and "") or ""
    # Infer ledger type from path param? Use body instead.
    raise HTTPException(400, "Use /ledgers/<type> endpoints")

async def _fetch_ledger_data(req: LedgerRequest, ltype: str):
    start, end, months, label = await _resolve_period(req)
    if ltype == "sales":
        data = await build_sales_register(req.center, start, end)
    elif ltype == "expenses":
        data = await build_expense_register(req.center, start, end)
    elif ltype == "cash":
        data = await build_cash_book(req.center, start, end)
    elif ltype == "bank":
        data = await build_bank_book(req.center, start, end)
    elif ltype == "commission":
        data = await build_commission_ledger(req.center, months)
    elif ltype == "loans":
        data = await build_loan_ledger(req.center, months)
    elif ltype == "payroll":
        data = await build_payroll_register(req.center, months)
    elif ltype == "gst":
        data = await build_gst_summary(req.center, start, end, months)
    elif ltype == "pnl":
        data = await build_monthly_pnl(req.center, months)
    elif ltype == "owner":
        data = await build_franchise_owner_ledger(req.center, months)
    else:
        raise HTTPException(400, f"Unknown ledger type: {ltype}")
    return data, label, start, end, months

def _render_ledger(ltype: str, data: Dict[str, Any], center: str, label: str, fmt: str,
                   country: Optional[str] = "India") -> Tuple[bytes, str, str]:
    title = LEDGER_TYPES.get(ltype, ltype.title())
    subtitle = f"Center: {center} · Period: {label} · Generated: {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')}"
    if fmt == "pdf":
        if ltype == "sales":
            sections = [("Daily Sales Breakdown (inclusive of GST)", _sales_to_table(data))]
        elif ltype == "expenses":
            sections = [("Expense Register", _expense_to_table(data))]
            # Category summary
            cat_rows = [["Category", "Amount"]] + [[k, _inr(v)] for k, v in sorted(data["by_category"].items(), key=lambda x: -x[1])]
            cat_rows.append(["TOTAL", _inr(data["total"])])
            sections.append(("Category-wise Summary", cat_rows))
        elif ltype == "cash":
            sections = [("Cash Book — Daily", _cash_to_table(data))]
        elif ltype == "bank":
            sections = [("Bank Book — Daily", _bank_to_table(data))]
        elif ltype == "commission":
            sections = [("Commission Ledger", _comm_to_table(data))]
        elif ltype == "loans":
            sections = _loan_to_tables(data) or [("Loans", [["No entries"]])]
        elif ltype == "payroll":
            sections = [("Payroll Register", _payroll_to_table(data))]
        elif ltype == "gst":
            sections = [("GST Summary", _gst_to_table(data)),
                        ("Note", [["Info"], [data.get("note", "")]])]
        elif ltype == "pnl":
            sections = [("Month-wise P&L", _pnl_to_table(data))]
        elif ltype == "owner":
            sections = [("Franchise Owner — Running Account with HQ", _owner_ledger_to_table(data))]
            f = data.get("franchise", {})
            _overseas_owner = bool(data.get("overseas"))
            franchise_details = [["Field", "Value"],
                                 ["Franchise Code", f.get("code") or "-"],
                                 ["Franchise Name", f.get("name") or "-"],
                                 ["Revenue / Profit Share %", f"{f.get('revenue_share_percent', 0)}%"]]
            if _overseas_owner:
                franchise_details.append(["MFPL Royalty (cumulative accrued)",
                                          _inr(data.get("total_mfpl_accrued", 0))])
            else:
                franchise_details.append(["Monthly Guarantee (MG)", _inr(f.get("monthly_guarantee", 0))])
            franchise_details.append(["Closing Balance", _inr(data.get("closing_balance", 0))])
            sections.append(("Franchise Details", franchise_details))

            # Eligible Rev Share Base — explicit formula breakout right before
            # the Final Payout block, so the franchise owner can trace exactly
            # how the payout base is calculated:
            #   Sales − Commission − Commission GST − GST on Sales
            pt = data.get("period_totals") or {}
            if pt and pt.get("total_sales", 0) > 0:
                sections.append(("Net Revenue Calculation", [
                    ["Description", "Amount"],
                    ["Total Sales", _inr(pt.get("total_sales", 0))],
                    ["Less: Commission (excl. GST)", _inr(pt.get("total_commission_base", 0))],
                    ["Less: Commission GST", _inr(pt.get("total_commission_gst", 0))],
                    ["Less: GST on Eligible Sales", _inr(pt.get("total_gst_on_sales", 0))],
                    ["Eligible Rev Share Base (Net Revenue)", _inr(pt.get("eligible_rev_share_base", 0))],
                ]))

            # Final Payout block — mirrors PIB Section 8B & MIS Franchise PDF.
            # Payout base = Revenue Share + MG top-up = MAX(rev_share, MG) per
            # month, then summed across the period. GST is applied on that
            # payout, NOT on the bare revenue share. Skip silently when the
            # franchise has no payout (no revenue share AND no MG top-up).
            total_rs = float(data.get("total_rev_share") or 0)
            total_mg = float(data.get("total_mg_topup") or 0)
            total_mfpl = float(data.get("total_mfpl_accrued") or 0)
            payout_base = total_rs + total_mg
            if payout_base > 0:
                if (country or "India").lower() == "india":
                    cgst = round(payout_base * 9 / 100, 2)
                    sgst = round(payout_base * 9 / 100, 2)
                    payout_label = (f"Payout for {label} "
                                    f"(MG ₹{total_mg:,.2f} + Rev Share ₹{total_rs:,.2f})"
                                    if total_mg > 0 else
                                    f"Revenue Share Payable for {label}")
                    sections.append(("Final Payout (Payout × GST)", [
                        ["Description", "Amount"],
                        [payout_label, _inr(payout_base)],
                        ["Add: CGST @ 9%", _inr(cgst)],
                        ["Add: SGST @ 9%", _inr(sgst)],
                        ["Total Final Payout (incl. 18% GST)", _inr(round(payout_base + cgst + sgst, 2))],
                    ]))
                else:
                    gst_amt = round(payout_base * 10 / 100, 2)
                    # Overseas: Profit Share only (no MG). Show MFPL accrued as a separate liability row.
                    payout_label = f"Profit Share Payable for {label}"
                    final_rows = [
                        ["Description", "Amount"],
                        [payout_label, _inr(payout_base)],
                        ["Add: GST @ 10%", _inr(gst_amt)],
                        ["Total Final Payout (incl. 10% GST)", _inr(round(payout_base + gst_amt, 2))],
                    ]
                    if total_mfpl > 0:
                        final_rows.append([
                            "MFPL Royalty Accrued (cumulative liability, 5% of Net Sales)",
                            _inr(total_mfpl),
                        ])
                    sections.append(("Final Payout (Payout × GST)", final_rows))
        else:
            sections = [("Data", [[str(data)]])]
        pdf = _render_pdf(title, subtitle, sections, country=country)
        return pdf, "application/pdf", f"{ltype}_{center}_{label}.pdf"
    elif fmt == "excel":
        if ltype == "sales":
            sheets = [("Sales Register", _sales_to_excel(data))]
        elif ltype == "expenses":
            sheets = [("Expense Register", _expense_to_excel(data))]
            cat_sheet = [["Category", "Amount"]] + [[k, v] for k, v in sorted(data["by_category"].items(), key=lambda x: -x[1])] + [["TOTAL", data["total"]]]
            sheets.append(("Category Summary", cat_sheet))
        elif ltype == "cash":
            sheets = [("Cash Book", _cash_to_excel(data))]
        elif ltype == "bank":
            sheets = [("Bank Book", _bank_to_excel(data))]
        elif ltype == "commission":
            sheets = [("Commission Ledger", _comm_to_excel(data))]
        elif ltype == "loans":
            sheets = _loan_to_excel_sheets(data)
        elif ltype == "payroll":
            sheets = [("Payroll Register", _payroll_to_excel(data))]
        elif ltype == "gst":
            sheets = [("GST Summary", _gst_to_excel(data))]
        elif ltype == "pnl":
            sheets = [("Monthly P&L", _pnl_to_excel(data))]
        elif ltype == "owner":
            sheets = [("Owner Ledger", _owner_ledger_to_excel(data))]
        else:
            sheets = [("Data", [["No data"]])]
        xlsx = _render_excel(sheets)
        return xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{ltype}_{center}_{label}.xlsx"
    else:  # json
        import json as _json
        return _json.dumps(data, default=str).encode(), "application/json", f"{ltype}_{center}_{label}.json"

def _type_endpoint(ltype: str):
    async def endpoint(req: LedgerRequest):
        session = verify_token(req.token)
        _check(session)
        # Owner ledger requires ledger access OR franchise owner of this center
        if ltype == "owner":
            if not (_has_ledger_access(session) or (_is_franchise_owner(session) and (session.get("franchise_center") == req.center or session.get("center") == req.center))):
                raise HTTPException(403, "Not authorized for Franchise Owner Ledger")
        else:
            if not _has_ledger_access(session):
                # Franchise owner: allow if Accounts has released the report for this center+month
                # (covers single-month period_type='month'; FY view always restricted to staff).
                allowed = False
                if (_is_franchise_owner(session)
                    and (session.get("franchise_center") == req.center or session.get("center") == req.center)
                    and (req.period_type or "").lower() == "month"
                    and req.month):
                    # Either:
                    #   (a) the general monthly Owner Report has been released
                    #       (no report_type, ready=True), or
                    #   (b) Accounts explicitly released ledgers for this month
                    #       (report_type='owner_ledger', released=True)
                    # unlocks ledger downloads for the franchise owner.
                    vis_general = await db.owner_report_visibility.find_one(
                        {"center": req.center, "month": req.month,
                         "report_type": {"$exists": False}},
                        {"_id": 0}
                    )
                    vis_ledger = await db.owner_report_visibility.find_one(
                        {"center": req.center, "month": req.month,
                         "report_type": "owner_ledger"},
                        {"_id": 0}
                    )
                    if (vis_general and vis_general.get("ready")) or (vis_ledger and vis_ledger.get("released")):
                        allowed = True
                if not allowed:
                    raise HTTPException(403, "This ledger is not available — ask Accounts to release the monthly report first")
        data, label, _start, _end, _months = await _fetch_ledger_data(req, ltype)
        fmt = (req.fmt or "pdf").lower()
        if fmt == "json":
            return {"success": True, "ledger": ltype, "center": req.center, "period": label, "data": data}
        # Resolve country for signature entity (Manaswini Foods PVT vs Purnabramha LLC PTY LTD)
        country = "India"
        cdoc = await db.centers.find_one({"code": req.center}, {"_id": 0, "country": 1})
        if cdoc and cdoc.get("country"):
            country = cdoc["country"]
        content, mime, filename = _render_ledger(ltype, data, req.center, label, fmt, country=country)
        return Response(content=content, media_type=mime, headers={"Content-Disposition": f"attachment; filename={filename}"})
    endpoint.__name__ = f"ledger_{ltype}"
    return endpoint

# Register endpoints dynamically
for _ltype in LEDGER_TYPES:
    router.post(f"/{_ltype}")(_type_endpoint(_ltype))

# =========================================================
# CA Bundle — zip everything
# =========================================================
@router.post("/bundle")
async def ca_bundle(req: BundleRequest):
    session = verify_token(req.token)
    _check(session)
    if not _has_ledger_access(session):
        raise HTTPException(403, "CA Bundle is restricted to Super Admin / Admin / Accounts roles")
    if req.period_type == "month":
        if not req.month:
            raise HTTPException(400, "month required")
        start, end = _month_range(req.month)
        months = [req.month]
        label = req.month
    else:
        if not req.fy_start_year:
            raise HTTPException(400, "fy_start_year required")
        start, end, months = _fy_range(int(req.fy_start_year))
        label = f"FY{req.fy_start_year}-{req.fy_start_year+1 - 2000:02d}"

    # Build all ledgers
    ledgers_data = {}
    ledgers_data["sales"] = await build_sales_register(req.center, start, end)
    ledgers_data["expenses"] = await build_expense_register(req.center, start, end)
    ledgers_data["cash"] = await build_cash_book(req.center, start, end)
    ledgers_data["bank"] = await build_bank_book(req.center, start, end)
    ledgers_data["commission"] = await build_commission_ledger(req.center, months)
    ledgers_data["loans"] = await build_loan_ledger(req.center, months)
    ledgers_data["payroll"] = await build_payroll_register(req.center, months)
    ledgers_data["gst"] = await build_gst_summary(req.center, start, end, months)
    ledgers_data["pnl"] = await build_monthly_pnl(req.center, months)
    ledgers_data["owner"] = await build_franchise_owner_ledger(req.center, months)

    # Resolve country for signature entity
    country = "India"
    cdoc = await db.centers.find_one({"code": req.center}, {"_id": 0, "country": 1})
    if cdoc and cdoc.get("country"):
        country = cdoc["country"]

    # Build ZIP
    zip_buf = BytesIO()
    with ZipFile(zip_buf, "w", ZIP_DEFLATED) as zf:
        # PDFs
        for ltype, data in ledgers_data.items():
            pdf, _mime, _fn = _render_ledger(ltype, data, req.center, label, "pdf", country=country)
            zf.writestr(f"01_PDFs/{ltype}_{req.center}_{label}.pdf", pdf)
            xlsx, _mime, _fn = _render_ledger(ltype, data, req.center, label, "excel", country=country)
            zf.writestr(f"02_Excel/{ltype}_{req.center}_{label}.xlsx", xlsx)

        # Bills — fetch all expense attachments + invoice group attachments for the period
        if req.include_bills:
            try:
                expenses = ledgers_data["expenses"]["rows"]
                # Fetch all attachments for expenses in period
                exp_docs = await db.expenses.find(
                    {"center": req.center, "date": {"$gte": start, "$lt": end}},
                    {"_id": 1, "expense_id": 1, "date": 1, "description": 1, "invoice_group_id": 1}
                ).to_list(10000)
                exp_ids = [str(e.get("expense_id") or e["_id"]) for e in exp_docs]
                grp_ids = list({e.get("invoice_group_id") for e in exp_docs if e.get("invoice_group_id")})

                att_query = {
                    "$or": [
                        {"expense_id": {"$in": exp_ids}},
                        {"invoice_group_id": {"$in": grp_ids}},
                    ],
                    "is_deleted": {"$ne": True},
                    "center": req.center,
                }
                attachments = await db.expense_attachments.find(att_query, {"_id": 0}).to_list(5000)
                # Stream each attachment content
                from routes.documents import get_object  # type: ignore
                added = 0
                for att in attachments:
                    try:
                        blob = get_object(att.get("storage_path"))
                        if not blob:
                            continue
                        fname = att.get("original_filename") or f"{att.get('attachment_id')}.bin"
                        # Find matching expense for folder name
                        exp = next((e for e in exp_docs if str(e.get("expense_id") or e["_id"]) == att.get("expense_id")), None)
                        folder_date = (exp.get("date") if exp else None) or (att.get("created_at") or "")[:10] or "misc"
                        zf.writestr(f"03_Bills/{folder_date}/{att.get('attachment_id')}__{fname}", blob)
                        added += 1
                    except Exception as e:
                        logger.warning(f"Could not add bill {att.get('attachment_id')}: {e}")
                zf.writestr("03_Bills/_README.txt", f"{added} bill(s) attached for period {label}.\nOrganized by expense date.\n")
            except Exception as e:
                logger.warning(f"Bills packaging skipped: {e}")
                zf.writestr("03_Bills/_README.txt", f"Bills could not be packaged: {e}")

        # README
        readme = (
            f"CA Bundle — {req.center} — {label}\n"
            f"Generated: {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')}\n\n"
            "Contents:\n"
            "  01_PDFs/  — Printable ledger reports\n"
            "  02_Excel/ — Editable ledger workbooks\n"
            "  03_Bills/ — Bill attachments, organized by expense date\n\n"
            "Ledgers included:\n"
            + "\n".join(f"  - {name}" for name in LEDGER_TYPES.values())
            + "\n\n"
            "Notes for CA:\n"
            "  - Output GST @ 5% computed on food service sales (inclusive basis).\n"
            "  - Input GST from expenses is NOT auto-tagged; please verify with vendor invoices.\n"
            "  - Commission GST charged by aggregators is reported for information.\n"
            "  - Payroll shows active employees with current salary; attendance-based actuals differ per month.\n"
            "  - Fixed asset register not maintained in the app — please provide separately.\n"
        )
        zf.writestr("00_README.txt", readme)

    zip_buf.seek(0)
    filename = f"CA_Bundle_{req.center}_{label}.zip"
    return Response(
        content=zip_buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# =========================================================
# Owner Ledger release / visibility — hooks into owner_report_visibility pattern
# =========================================================
@router.post("/owner/release")
async def release_owner_ledger(req: OwnerLedgerSendRequest):
    session = verify_token(req.token)
    _check(session)
    if not _has_ledger_access(session):
        raise HTTPException(403, "Only Super Admin / Admin / Accounts can release owner ledgers")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "center": req.center,
        "month": req.month,
        "report_type": "owner_ledger",
        "released": req.action == "release",
        "released_at": now if req.action == "release" else None,
        "released_by": session.get("managerName", "Unknown"),
        "updated_at": now,
    }
    await db.owner_report_visibility.update_one(
        {"center": req.center, "month": req.month, "report_type": "owner_ledger"},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return {"success": True, "released": req.action == "release"}

@router.post("/owner/visibility")
async def check_owner_ledger_visibility(req: dict = Body(...)):
    session = verify_token(req.get("token"))
    _check(session)
    center = req.get("center")
    month = req.get("month")
    doc = await db.owner_report_visibility.find_one(
        {"center": center, "month": month, "report_type": "owner_ledger"}, {"_id": 0}
    )
    return {"visible": bool(doc and doc.get("released")), "metadata": doc or {}}

@router.post("/owner/list")
async def list_released_owner_ledgers(req: dict = Body(...)):
    """Franchise owner calls this to see what months have been released for them.
    Returns months where either:
      - owner_report_visibility {ready: True}  (full monthly report released → all ledgers unlocked)
      - or owner_report_visibility {report_type:"owner_ledger", released: True}  (legacy owner ledger only)
    Each entry indicates which ledger types are accessible.
    """
    session = verify_token(req.get("token"))
    _check(session)
    # Resolve center: franchise owner uses franchise_center/center
    center = (req.get("center") or session.get("franchise_center") or session.get("center") or "").upper()
    if not center:
        raise HTTPException(400, "center required")
    # Pull both visibility flavours
    docs = await db.owner_report_visibility.find(
        {"center": center}, {"_id": 0}
    ).sort("month", -1).to_list(120)
    by_month: dict = {}
    for d in docs:
        m = d.get("month")
        if not m:
            continue
        rec = by_month.setdefault(m, {
            "month": m, "released_at": None,
            "report_ready": False, "owner_ledger_released": False,
        })
        rt = d.get("report_type") or "monthly_report"
        if rt == "owner_ledger" and d.get("released"):
            rec["owner_ledger_released"] = True
            rec["released_at"] = d.get("released_at") or rec["released_at"]
        elif d.get("ready"):
            rec["report_ready"] = True
            rec["released_at"] = d.get("released_at") or d.get("updated_at") or rec["released_at"]
    months = []
    for m in sorted(by_month.keys(), reverse=True):
        rec = by_month[m]
        # Available ledger types for this month
        if rec["report_ready"]:
            avail = list(LEDGER_TYPES.keys())  # All ledgers unlocked
        elif rec["owner_ledger_released"]:
            avail = ["owner"]
        else:
            continue
        rec["available_ledgers"] = avail
        months.append(rec)
    return {
        "success": True, "center": center,
        "months": months,
        "ledger_labels": LEDGER_TYPES,
    }

@router.post("/types")
async def list_ledger_types(req: dict = Body(...)):
    session = verify_token(req.get("token"))
    _check(session)
    return {
        "ledger_types": [{"key": k, "label": v} for k, v in LEDGER_TYPES.items()],
        "has_access": _has_ledger_access(session),
        "is_franchise_owner": _is_franchise_owner(session),
    }
