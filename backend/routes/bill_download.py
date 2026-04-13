# =======================================
# Bill Download Access Module
# Multi-download, ZIP, for franchise owners
# =======================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from datetime import datetime, timezone
import logging
import io
import zipfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bill-download", tags=["Bill Download"])

db = None
verify_token = None
has_admin_access = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_has_admin_access(func):
    global has_admin_access
    has_admin_access = func


DOC_TYPES = ["Sales Bill", "Expense Bill", "Invoice", "Purchase Bill", "Platform Settlement", "Supporting Document", "Account Document", "Other"]


@router.post("/list")
async def list_bills(data: dict):
    """List bills/documents for a center with filters."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    is_admin = has_admin_access(session)
    query = {}

    # Role-based center access
    if not is_admin:
        user_center = session.get("center", "")
        # Check franchise ownership
        franchise = await db.franchises.find_one(
            {"$or": [{"owners": session.get("mobile")}, {"center_code": user_center}]},
            {"_id": 0, "center_code": 1}
        )
        if franchise:
            query["center"] = franchise.get("center_code", user_center)
        else:
            query["center"] = user_center
    elif data.get("center"):
        query["center"] = data["center"].upper()

    # Filters
    if data.get("doc_type"):
        query["doc_type"] = data["doc_type"]
    if data.get("expense_head"):
        query["expense_head"] = data["expense_head"]
    if data.get("uploaded_by"):
        query["uploaded_by"] = data["uploaded_by"]
    if data.get("month"):
        query["date"] = {"$regex": f"^{data['month']}"}
    elif data.get("date_from") or data.get("date_to"):
        dq = {}
        if data.get("date_from"):
            dq["$gte"] = data["date_from"]
        if data.get("date_to"):
            dq["$lte"] = data["date_to"]
        query["date"] = dq
    elif data.get("year"):
        query["date"] = {"$regex": f"^{data['year']}"}

    bills = await db.bills.find(query, {"_id": 0}).sort("date", -1).to_list(5000)

    # Also search in expenses collection for bills with attachments
    exp_query = {}
    if query.get("center"):
        exp_query["center"] = query["center"]
    if data.get("month"):
        exp_query["date"] = {"$regex": f"^{data['month']}"}
    elif query.get("date"):
        exp_query["date"] = query["date"]
    exp_query["bill_url"] = {"$exists": True, "$ne": ""}

    expense_bills = await db.expenses.find(exp_query, {"_id": 0}).sort("date", -1).to_list(5000)

    # Convert expense bills to bill format
    for eb in expense_bills:
        bills.append({
            "bill_id": f"EXP-{eb.get('expense_id', '')}",
            "center": eb.get("center", ""),
            "date": eb.get("date", ""),
            "doc_type": "Expense Bill",
            "description": eb.get("description", eb.get("expense_type", "")),
            "amount": eb.get("amount", 0),
            "file_url": eb.get("bill_url", ""),
            "file_name": eb.get("bill_filename", "expense_bill"),
            "expense_head": eb.get("expense_type", ""),
            "uploaded_by": eb.get("created_by", ""),
            "uploaded_at": eb.get("created_at", ""),
        })

    return {
        "bills": bills,
        "count": len(bills),
        "doc_types": DOC_TYPES,
    }


@router.post("/upload")
async def upload_bill(data: dict):
    """Upload a bill document (Admin / Manager)."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    import uuid
    bill_id = f"BILL-{str(uuid.uuid4())[:8].upper()}"
    bill = {
        "bill_id": bill_id,
        "center": (data.get("center") or session.get("center", "")).upper(),
        "date": data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "doc_type": data.get("doc_type", "Other"),
        "description": data.get("description", ""),
        "amount": float(data.get("amount", 0)),
        "file_url": data.get("file_url", ""),
        "file_name": data.get("file_name", ""),
        "expense_head": data.get("expense_head", ""),
        "uploaded_by": session.get("managerName", session.get("mobile", "")),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bills.insert_one(bill)
    return {"success": True, "bill_id": bill_id, "message": "Bill uploaded"}


@router.post("/download-zip")
async def download_zip(data: dict):
    """Download multiple bills as a ZIP file."""
    import urllib.request

    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    is_admin = has_admin_access(session)
    center = (data.get("center") or session.get("center", "")).upper()

    # Franchise owner access check
    if not is_admin:
        user_center = session.get("center", "")
        franchise = await db.franchises.find_one(
            {"$or": [{"owners": session.get("mobile")}, {"center_code": user_center}]},
            {"_id": 0, "center_code": 1}
        )
        allowed_center = franchise.get("center_code", user_center) if franchise else user_center
        if center != allowed_center:
            raise HTTPException(403, "Access denied to this center's bills")

    # Get bill IDs or query
    bill_ids = data.get("bill_ids", [])
    query = {"center": center}

    if bill_ids:
        query["$or"] = [{"bill_id": {"$in": bill_ids}}, {"bill_id": {"$in": bill_ids}}]
    else:
        if data.get("month"):
            query["date"] = {"$regex": f"^{data['month']}"}
        elif data.get("date_from") and data.get("date_to"):
            query["date"] = {"$gte": data["date_from"], "$lte": data["date_to"]}
        if data.get("doc_type"):
            query["doc_type"] = data["doc_type"]

    bills = await db.bills.find(query, {"_id": 0}).to_list(5000)

    # Also check expenses with bill_url
    if not bill_ids:
        exp_q = {"center": center, "bill_url": {"$exists": True, "$ne": ""}}
        if data.get("month"):
            exp_q["date"] = {"$regex": f"^{data['month']}"}
        elif data.get("date_from") and data.get("date_to"):
            exp_q["date"] = {"$gte": data["date_from"], "$lte": data["date_to"]}
        expense_bills = await db.expenses.find(exp_q, {"_id": 0}).to_list(5000)
        for eb in expense_bills:
            bills.append({
                "bill_id": f"EXP-{eb.get('expense_id', '')}",
                "date": eb.get("date", ""),
                "doc_type": "Expense Bill",
                "file_url": eb.get("bill_url", ""),
                "file_name": eb.get("bill_filename", f"expense_{eb.get('date','')}"),
            })

    if not bills:
        raise HTTPException(404, "No bills found for the given criteria")

    # Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for bill in bills:
            file_url = bill.get("file_url", "")
            if not file_url:
                continue
            try:
                req = urllib.request.Request(file_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    file_data = resp.read()
                # Build neat filename
                doc_type = bill.get("doc_type", "Other").replace(" ", "_")
                date_str = bill.get("date", "unknown")
                bill_id = bill.get("bill_id", "")
                ext = file_url.rsplit(".", 1)[-1][:5] if "." in file_url else "pdf"
                filename = f"{center}/{doc_type}/{date_str}_{bill_id}.{ext}"
                zf.writestr(filename, file_data)
            except Exception as e:
                logger.error(f"Failed to download bill {bill.get('bill_id')}: {e}")

    zip_buffer.seek(0)
    zip_data = zip_buffer.getvalue()

    if len(zip_data) < 50:
        raise HTTPException(404, "No downloadable files found")

    period = data.get("month") or f"{data.get('date_from', '')}_{data.get('date_to', '')}" or "all"
    filename = f"Bills_{center}_{period}.zip"

    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
