# =======================================
# Loan Entry Routes
# Working Capital Loan Tracking
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/loan-entries", tags=["Loan Entries"])

# Database reference
db = None

def set_db(database):
    global db
    db = database

# Verify token function (will be set from main server)
verify_token_async = None

def set_verify_token_async(func):
    global verify_token_async
    verify_token_async = func

# =======================================
# MODELS
# =======================================

class LoanEntryCreate(BaseModel):
    center: str
    amount: float
    loan_date: str  # YYYY-MM-DD
    reason: str
    notes: Optional[str] = ""

class LoanRepayment(BaseModel):
    amount: float
    repayment_date: str
    notes: Optional[str] = ""

# =======================================
# HELPER FUNCTIONS
# =======================================

async def check_access(token: str):
    """Verify token and return session"""
    if not token:
        raise HTTPException(401, "Authentication required")
    
    session = await db.sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    
    return session

async def get_center_details(center_code: str):
    """Get center details"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        raise HTTPException(404, f"Center {center_code} not found")
    return center

async def get_franchise_for_center(center_code: str):
    """Get linked franchise for a center"""
    center = await db.centers.find_one({"code": center_code}, {"_id": 0})
    if not center:
        return None
    
    franchise_code = center.get("franchise_code")
    if franchise_code:
        franchise = await db.franchises.find_one({"franchise_code": franchise_code}, {"_id": 0})
        if franchise:
            return franchise
    
    # Try to match by city for Perth
    if "perth" in center_code.lower():
        franchise = await db.franchises.find_one(
            {"city": {"$regex": "perth", "$options": "i"}, "status": {"$ne": "Deleted"}},
            {"_id": 0}
        )
        if franchise:
            return franchise
    
    return None

def generate_loan_id(center: str) -> str:
    """Generate unique loan ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"LOAN-{center}-{timestamp}"

# =======================================
# LOAN ENTRY ENDPOINTS
# =======================================

@router.post("/create")
async def create_loan_entry(data: dict):
    """Create a new loan entry (using working capital)"""
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin or Admin can create loan entries
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Only Admin can create loan entries")
    
    # Validate required fields
    required_fields = ["center", "amount", "loan_date", "reason"]
    missing_fields = [f for f in required_fields if not data.get(f)]
    if missing_fields:
        raise HTTPException(422, f"Missing required fields: {', '.join(missing_fields)}")
    
    center = data.get("center")
    source_center = data.get("source_center", "")  # Center giving the loan
    amount = float(data.get("amount", 0))
    
    if amount <= 0:
        raise HTTPException(400, "Loan amount must be positive")
    
    # Get center and franchise info
    center_info = await get_center_details(center)
    franchise = await get_franchise_for_center(center)
    
    # Source center info (who is giving the loan)
    source_center_info = None
    source_franchise = None
    if source_center:
        try:
            source_center_info = await get_center_details(source_center)
            source_franchise = await get_franchise_for_center(source_center)
        except Exception:
            pass
    
    # Note: Per business requirement, loan amounts are NOT capped by the center's
    # working capital. Loans may be sourced from other centers or HQ, so any amount
    # is allowed. We only validate that the amount is positive (already done above).
    
    # Create "Loan Taken" entry for the borrowing center
    loan_id = generate_loan_id(center)
    now = datetime.now(timezone.utc).isoformat()
    user = session.get("managerName", "Unknown")
    
    loan_doc = {
        "loan_id": loan_id,
        "center": center,
        "center_name": center_info.get("name", center),
        "franchise_code": franchise.get("franchise_code") if franchise else None,
        "franchise_name": franchise.get("franchise_name") if franchise else None,
        "loan_type": "taken",  # taken or given
        "source_center": source_center,
        "source_center_name": source_center_info.get("name", source_center) if source_center_info else source_center,
        "linked_loan_id": "",  # Will be set after creating the mirror
        "amount": amount,
        "loan_date": data.get("loan_date"),
        "reason": data.get("reason"),
        "notes": data.get("notes", ""),
        "status": "active",
        "total_repaid": 0,
        "repayments": [],
        "working_capital_at_time": franchise.get("working_capital", 0) if franchise else 0,
        "created_at": now,
        "created_by": user,
        "updated_at": now
    }
    
    await db.loan_entries.insert_one(loan_doc)
    
    # Auto-create Other Income (memo) entry for the borrower center
    try:
        from routes.other_income import auto_create_loan_taken_income
        await auto_create_loan_taken_income(
            center=center,
            amount=amount,
            loan_date=data.get("loan_date"),
            source_center=source_center or "External",
            loan_id=loan_id,
            created_by=user,
        )
    except Exception as e:
        logger.warning(f"Failed to auto-create Other Income for loan {loan_id}: {e}")
    
    # Auto-create "Loan Given" mirror entry for the source center
    given_loan_id = ""
    if source_center:
        given_loan_id = generate_loan_id(source_center) + "-G"
        given_doc = {
            "loan_id": given_loan_id,
            "center": source_center,
            "center_name": source_center_info.get("name", source_center) if source_center_info else source_center,
            "franchise_code": source_franchise.get("franchise_code") if source_franchise else None,
            "franchise_name": source_franchise.get("franchise_name") if source_franchise else None,
            "loan_type": "given",
            "target_center": center,
            "target_center_name": center_info.get("name", center),
            "linked_loan_id": loan_id,
            "amount": amount,
            "loan_date": data.get("loan_date"),
            "reason": f"Loan given to {center}: {data.get('reason', '')}",
            "notes": data.get("notes", ""),
            "status": "active",
            "total_repaid": 0,
            "repayments": [],
            "created_at": now,
            "created_by": user,
            "updated_at": now
        }
        await db.loan_entries.insert_one(given_doc)
        
        # Link the taken loan to the given loan
        await db.loan_entries.update_one(
            {"loan_id": loan_id},
            {"$set": {"linked_loan_id": given_loan_id}}
        )
    
    return {
        "success": True,
        "message": f"Loan entry created{' (mirrored to ' + source_center + ')' if source_center else ''}",
        "loan_id": loan_id,
        "given_loan_id": given_loan_id,
        "loan": {
            "loan_id": loan_id,
            "amount": amount,
            "center": center,
            "source_center": source_center,
            "loan_date": data.get("loan_date"),
            "status": "active"
        }
    }

@router.post("/list")
async def list_loan_entries(data: dict):
    """List loan entries for a center or all centers"""
    token = data.get("token")
    session = await check_access(token)
    
    center = data.get("center")
    status_filter = data.get("status")  # active, partially_repaid, fully_repaid, or None for all
    
    query = {}
    if center:
        query["center"] = center
    if status_filter:
        query["status"] = status_filter
    
    loans = await db.loan_entries.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Separate into taken and given
    loans_taken = [l for l in loans if l.get("loan_type", "taken") != "given"]
    loans_given = [l for l in loans if l.get("loan_type") == "given"]
    
    # Calculate summary
    total_taken = sum(loan.get("amount", 0) for loan in loans_taken)
    total_taken_repaid = sum(loan.get("total_repaid", 0) for loan in loans_taken)
    total_given = sum(loan.get("amount", 0) for loan in loans_given)
    total_given_repaid = sum(loan.get("total_repaid", 0) for loan in loans_given)
    
    active_loans = [l for l in loans if l.get("status") == "active"]
    partially_repaid = [l for l in loans if l.get("status") == "partially_repaid"]
    fully_repaid_list = [l for l in loans if l.get("status") == "fully_repaid"]
    
    return {
        "success": True,
        "loans": loans,
        "loans_taken": loans_taken,
        "loans_given": loans_given,
        "summary": {
            "total_loaned": total_taken,
            "total_repaid": total_taken_repaid,
            "total_outstanding": total_taken - total_taken_repaid,
            "total_given": total_given,
            "total_given_repaid": total_given_repaid,
            "total_given_outstanding": total_given - total_given_repaid,
            "active_count": len(active_loans),
            "partially_repaid_count": len(partially_repaid),
            "fully_repaid_count": len(fully_repaid_list)
        }
    }

@router.post("/get/{loan_id}")
async def get_loan_entry(loan_id: str, data: dict):
    """Get details of a specific loan entry"""
    token = data.get("token")
    session = await check_access(token)
    
    loan = await db.loan_entries.find_one({"loan_id": loan_id}, {"_id": 0})
    if not loan:
        raise HTTPException(404, "Loan entry not found")
    
    return {"success": True, "loan": loan}

@router.post("/add-repayment/{loan_id}")
async def add_repayment(loan_id: str, data: dict):
    """Add a repayment to a loan entry"""
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin or Admin can add repayments
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Only Admin can add repayments")
    
    loan = await db.loan_entries.find_one({"loan_id": loan_id})
    if not loan:
        raise HTTPException(404, "Loan entry not found")
    
    if loan.get("status") == "fully_repaid":
        raise HTTPException(400, "This loan is already fully repaid")
    
    repayment_amount = float(data.get("amount", 0))
    repayment_date = data.get("repayment_date")
    
    if repayment_amount <= 0:
        raise HTTPException(400, "Repayment amount must be positive")
    
    if not repayment_date:
        raise HTTPException(400, "Repayment date is required")
    
    # Calculate outstanding
    outstanding = loan.get("amount", 0) - loan.get("total_repaid", 0)
    
    if repayment_amount > outstanding:
        raise HTTPException(400, f"Repayment amount ({repayment_amount}) exceeds outstanding ({outstanding})")
    
    # Add repayment
    repayment = {
        "amount": repayment_amount,
        "repayment_date": repayment_date,
        "notes": data.get("notes", ""),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "recorded_by": session.get("managerName", "Unknown")
    }
    
    new_total_repaid = loan.get("total_repaid", 0) + repayment_amount
    new_outstanding = loan.get("amount", 0) - new_total_repaid
    
    # Determine new status
    if new_outstanding <= 0:
        new_status = "fully_repaid"
    elif new_total_repaid > 0:
        new_status = "partially_repaid"
    else:
        new_status = "active"
    
    # Update loan
    await db.loan_entries.update_one(
        {"loan_id": loan_id},
        {
            "$push": {"repayments": repayment},
            "$set": {
                "total_repaid": new_total_repaid,
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Mirror repayment to linked loan (given/taken pair)
    linked_id = loan.get("linked_loan_id")
    if linked_id:
        linked_loan = await db.loan_entries.find_one({"loan_id": linked_id})
        if linked_loan:
            linked_new_repaid = linked_loan.get("total_repaid", 0) + repayment_amount
            linked_outstanding = linked_loan.get("amount", 0) - linked_new_repaid
            linked_status = "fully_repaid" if linked_outstanding <= 0 else ("partially_repaid" if linked_new_repaid > 0 else "active")
            await db.loan_entries.update_one(
                {"loan_id": linked_id},
                {
                    "$push": {"repayments": repayment},
                    "$set": {
                        "total_repaid": linked_new_repaid,
                        "status": linked_status,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
    
    return {
        "success": True,
        "message": f"Repayment of {repayment_amount} recorded",
        "new_total_repaid": new_total_repaid,
        "new_outstanding": new_outstanding,
        "new_status": new_status
    }

@router.post("/summary")
async def get_loan_summary(data: dict):
    """Get loan summary for a center"""
    token = data.get("token")
    session = await check_access(token)
    
    center = data.get("center")
    if not center:
        raise HTTPException(400, "Center is required")
    
    # Get franchise info for working capital
    franchise = await get_franchise_for_center(center)
    working_capital = franchise.get("working_capital", 0) if franchise else 0
    
    # Get all loans for this center
    loans = await db.loan_entries.find({"center": center}, {"_id": 0}).to_list(500)

    # Split by direction. "Outstanding" KPI must reflect only TAKEN loans
    # (money this center owes others). GIVEN loans are reported separately.
    loans_taken = [l for l in loans if l.get("loan_type", "taken") != "given"]
    loans_given = [l for l in loans if l.get("loan_type") == "given"]

    total_taken = sum(loan.get("amount", 0) for loan in loans_taken)
    total_taken_repaid = sum(loan.get("total_repaid", 0) for loan in loans_taken)
    total_taken_outstanding = total_taken - total_taken_repaid

    total_given = sum(loan.get("amount", 0) for loan in loans_given)
    total_given_repaid = sum(loan.get("total_repaid", 0) for loan in loans_given)
    total_given_outstanding = total_given - total_given_repaid

    # Working-capital utilisation is driven by TAKEN loans only
    available_working_capital = working_capital - total_taken_outstanding

    # Recent loans (last 5)
    recent_loans = sorted(loans, key=lambda x: x.get("created_at", ""), reverse=True)[:5]

    # Active loans counter (TAKEN only — matches the "Loans Outstanding" KPI label)
    active_loans = [l for l in loans_taken if l.get("status") in ["active", "partially_repaid"]]
    active_given = [l for l in loans_given if l.get("status") in ["active", "partially_repaid"]]

    return {
        "success": True,
        "center": center,
        "working_capital": {
            "total": working_capital,
            "utilized": total_taken_outstanding,
            "available": available_working_capital,
            "utilization_percentage": (total_taken_outstanding / working_capital * 100) if working_capital > 0 else 0
        },
        "loans": {
            "total_loaned": total_taken,
            "total_repaid": total_taken_repaid,
            "total_outstanding": total_taken_outstanding,
            "active_count": len(active_loans),
            "total_count": len(loans_taken)
        },
        "summary": {
            "total_taken": total_taken,
            "total_taken_outstanding": total_taken_outstanding,
            "total_given": total_given,
            "total_given_repaid": total_given_repaid,
            "total_given_outstanding": total_given_outstanding,
            "active_given_count": len(active_given),
        },
        "recent_loans": recent_loans,
        "active_loans": active_loans
    }

@router.post("/delete/{loan_id}")
async def delete_loan_entry(loan_id: str, data: dict):
    """Delete a loan entry and its linked mirror.
    Pass force=true to override the 'has repayments' guard.
    """
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin can delete
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can delete loan entries")
    
    force = bool(data.get("force", False))
    
    loan = await db.loan_entries.find_one({"loan_id": loan_id})
    if not loan:
        raise HTTPException(404, "Loan entry not found")
    
    if loan.get("total_repaid", 0) > 0 and not force:
        raise HTTPException(400, "Cannot delete loan with existing repayments. Pass force=true to override.")
    
    deleted_ids = [loan_id]
    
    # Cascade delete the mirrored loan (taken<->given pair)
    linked_id = loan.get("linked_loan_id")
    if linked_id:
        linked = await db.loan_entries.find_one({"loan_id": linked_id})
        if linked:
            await db.loan_entries.delete_one({"loan_id": linked_id})
            deleted_ids.append(linked_id)
    
    await db.loan_entries.delete_one({"loan_id": loan_id})
    
    # Cascade: remove auto-generated Other Income rows linked to these loans
    try:
        from routes.other_income import cascade_delete_for_loan
        await cascade_delete_for_loan(deleted_ids)
    except Exception as e:
        logger.warning(f"Other Income cascade delete failed: {e}")
    
    logger.info(f"Loan entries deleted by {session.get('managerName')}: {deleted_ids}")
    
    return {
        "success": True,
        "message": f"Deleted {len(deleted_ids)} loan entry/entries",
        "deleted_loan_ids": deleted_ids
    }


@router.post("/bulk-delete")
async def bulk_delete_loan_entries(data: dict):
    """Bulk delete loan entries by center and/or month.
    
    Body:
    - token: required
    - center: center code OR "all" (required)
    - month: YYYY-MM string (optional; if omitted, deletes ALL months for the center scope)
    - force: bool (optional, default False) - allow deleting loans with repayments
    - confirm: bool (required, must be true) - safety check
    """
    token = data.get("token")
    session = await check_access(token)
    
    # Only Super Admin can bulk delete
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can bulk delete loan entries")
    
    center = (data.get("center") or "").strip()
    month = (data.get("month") or "").strip()  # YYYY-MM
    force = bool(data.get("force", False))
    confirm = bool(data.get("confirm", False))
    
    if not center:
        raise HTTPException(400, "center is required ('all' or a center code)")
    
    if not confirm:
        raise HTTPException(400, "confirm=true is required to bulk delete")
    
    # Build query
    query: Dict[str, Any] = {}
    if center.lower() != "all":
        query["center"] = center
    
    if month:
        # Validate YYYY-MM
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            raise HTTPException(400, "month must be in YYYY-MM format")
        query["loan_date"] = {"$regex": f"^{month}-"}
    
    # Find candidates
    candidates = await db.loan_entries.find(query, {"_id": 0}).to_list(10000)
    
    if not candidates:
        return {
            "success": True,
            "message": "No loan entries matched the filter",
            "deleted_count": 0,
            "skipped_count": 0
        }
    
    # Build the full set of loan_ids to delete (cascade mirrors)
    loan_ids_to_delete = set()
    skipped_with_repayments = []
    
    for loan in candidates:
        if loan.get("total_repaid", 0) > 0 and not force:
            skipped_with_repayments.append(loan.get("loan_id"))
            continue
        loan_ids_to_delete.add(loan.get("loan_id"))
        linked = loan.get("linked_loan_id")
        if linked:
            loan_ids_to_delete.add(linked)
    
    deleted_count = 0
    if loan_ids_to_delete:
        result = await db.loan_entries.delete_many({"loan_id": {"$in": list(loan_ids_to_delete)}})
        deleted_count = result.deleted_count
        # Cascade: remove auto-generated Other Income rows
        try:
            from routes.other_income import cascade_delete_for_loan
            await cascade_delete_for_loan(list(loan_ids_to_delete))
        except Exception as e:
            logger.warning(f"Other Income cascade delete failed: {e}")
    
    logger.info(
        f"Bulk loan delete by {session.get('managerName')}: "
        f"center={center}, month={month or 'ALL'}, force={force}, "
        f"deleted={deleted_count}, skipped={len(skipped_with_repayments)}"
    )
    
    msg_parts = [f"Deleted {deleted_count} loan entries"]
    if center.lower() == "all":
        msg_parts.append("across all centers")
    else:
        msg_parts.append(f"for {center}")
    if month:
        msg_parts.append(f"in {month}")
    if skipped_with_repayments:
        msg_parts.append(f"({len(skipped_with_repayments)} skipped due to repayments — use force=true to override)")
    
    return {
        "success": True,
        "message": " ".join(msg_parts),
        "deleted_count": deleted_count,
        "skipped_count": len(skipped_with_repayments),
        "skipped_loan_ids": skipped_with_repayments
    }


# =======================================
# LOAN REPORT PDF
# =======================================

@router.post("/report/pdf")
async def generate_loan_report_pdf(data: dict):
    """Generate PDF loan report for a center with Purnabramha branding."""
    token = data.get("token")
    session = await check_access(token)
    
    center = data.get("center")
    if not center:
        raise HTTPException(400, "Center is required")
    
    # Get center and franchise info
    center_info = await get_center_details(center)
    franchise = await get_franchise_for_center(center)
    working_capital = franchise.get("working_capital", 0) if franchise else 0
    
    # Get all loans
    all_loans = await db.loan_entries.find({"center": center}, {"_id": 0}).sort("loan_date", -1).to_list(500)
    
    loans_taken = [l for l in all_loans if l.get("loan_type", "taken") != "given"]
    loans_given = [l for l in all_loans if l.get("loan_type") == "given"]
    
    total_taken = sum(l.get("amount", 0) for l in loans_taken)
    total_taken_repaid = sum(l.get("total_repaid", 0) for l in loans_taken)
    total_given = sum(l.get("amount", 0) for l in loans_given)
    total_given_repaid = sum(l.get("total_repaid", 0) for l in loans_given)
    
    # Generate PDF
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from fastapi.responses import Response
    import io
    
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(name='Brand', fontSize=18, textColor=colors.HexColor("#8B0000"), fontName='Helvetica-Bold', spaceAfter=2*mm))
    styles.add(ParagraphStyle(name='Sub', fontSize=10, textColor=colors.gray, spaceAfter=5*mm))
    styles.add(ParagraphStyle(name='Section', fontSize=13, textColor=colors.HexColor("#8B0000"), fontName='Helvetica-Bold', spaceBefore=6*mm, spaceAfter=3*mm))
    
    story = []
    
    # Header
    story.append(Paragraph("Purnabramha", styles['Brand']))
    story.append(Paragraph(f"Loan Report - {center} ({center_info.get('name', '')})", styles['Sub']))
    
    # Franchise Info
    if franchise:
        info_data = [
            ["Franchise Owner", franchise.get("owner_name", "N/A")],
            ["Center", f"{center} - {center_info.get('name', '')}"],
            ["City / State", f"{franchise.get('city', '')} / {franchise.get('state', '')}"],
            ["Working Capital", f"Rs. {working_capital:,.2f}"],
            ["Report Date", datetime.now().strftime("%d %b %Y")],
        ]
        info_table = Table(info_data, colWidths=[120, 350])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(info_table)
    
    # Summary
    story.append(Paragraph("Loan Summary", styles['Section']))
    summary_data = [
        ["Category", "Amount", "Repaid", "Outstanding"],
        ["Loans Taken", f"Rs. {total_taken:,.2f}", f"Rs. {total_taken_repaid:,.2f}", f"Rs. {total_taken - total_taken_repaid:,.2f}"],
        ["Loans Given", f"Rs. {total_given:,.2f}", f"Rs. {total_given_repaid:,.2f}", f"Rs. {total_given - total_given_repaid:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[120, 130, 130, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#8B0000")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    
    # Loans Taken Detail
    if loans_taken:
        story.append(Paragraph("Loans Taken (Borrowed)", styles['Section']))
        taken_data = [["Date", "Source Center", "Amount", "Reason", "Repaid", "Outstanding", "Status"]]
        for l in loans_taken:
            outstanding = l.get("amount", 0) - l.get("total_repaid", 0)
            taken_data.append([
                l.get("loan_date", ""),
                l.get("source_center", l.get("source_center_name", "N/A")),
                f"Rs. {l.get('amount', 0):,.2f}",
                (l.get("reason", "")[:30] + "..." if len(l.get("reason", "")) > 30 else l.get("reason", "")),
                f"Rs. {l.get('total_repaid', 0):,.2f}",
                f"Rs. {outstanding:,.2f}",
                l.get("status", "").replace("_", " ").title(),
            ])
        taken_table = Table(taken_data, colWidths=[60, 70, 75, 90, 70, 75, 60])
        taken_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (4, 0), (5, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8f8")]),
        ]))
        story.append(taken_table)
    
    # Loans Given Detail
    if loans_given:
        story.append(Paragraph("Loans Given (Lent to Other Centers)", styles['Section']))
        given_data = [["Date", "Given To", "Amount", "Reason", "Repaid", "Outstanding", "Status"]]
        for l in loans_given:
            outstanding = l.get("amount", 0) - l.get("total_repaid", 0)
            given_data.append([
                l.get("loan_date", ""),
                l.get("target_center", l.get("target_center_name", "N/A")),
                f"Rs. {l.get('amount', 0):,.2f}",
                (l.get("reason", "")[:30] + "..." if len(l.get("reason", "")) > 30 else l.get("reason", "")),
                f"Rs. {l.get('total_repaid', 0):,.2f}",
                f"Rs. {outstanding:,.2f}",
                l.get("status", "").replace("_", " ").title(),
            ])
        given_table = Table(given_data, colWidths=[60, 70, 75, 90, 70, 75, 60])
        given_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d9488")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('ALIGN', (4, 0), (5, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdfa")]),
        ]))
        story.append(given_table)
    
    # Repayment History
    all_repayments = []
    for l in all_loans:
        for r in l.get("repayments", []):
            loan_type = l.get("loan_type", "taken")
            counterpart = l.get("source_center") or l.get("target_center") or ""
            all_repayments.append({
                "date": r.get("repayment_date", ""),
                "loan_id": l.get("loan_id", ""),
                "type": "Taken" if loan_type != "given" else "Given",
                "counterpart": counterpart,
                "amount": r.get("amount", 0),
                "notes": r.get("notes", ""),
            })
    
    if all_repayments:
        all_repayments.sort(key=lambda x: x["date"], reverse=True)
        story.append(Paragraph("Repayment History", styles['Section']))
        rep_data = [["Date", "Loan ID", "Type", "Center", "Amount", "Notes"]]
        for r in all_repayments[:20]:
            rep_data.append([
                r["date"], r["loan_id"][-12:], r["type"], r["counterpart"],
                f"Rs. {r['amount']:,.2f}", r["notes"][:25]
            ])
        rep_table = Table(rep_data, colWidths=[65, 80, 45, 65, 75, 130])
        rep_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4b5563")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(rep_table)
    
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%d %b %Y %H:%M')} by {session.get('managerName', 'System')}", 
                           ParagraphStyle(name='Footer', fontSize=8, textColor=colors.gray)))
    
    doc.build(story)
    buf.seek(0)
    
    filename = f"Loan_Report_{center}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
