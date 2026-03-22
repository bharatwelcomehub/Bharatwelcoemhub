# =======================================
# Franchise Exit & Closure Module
# Manages franchise exits with proper documentation
# =======================================

from fastapi import APIRouter, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import logging
import os

router = APIRouter(prefix="/api/franchise-exit", tags=["Franchise Exit"])
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "purnabramha_db")
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# =======================================
# MODELS
# =======================================

class ExitInitiation(BaseModel):
    franchise_code: str
    exit_reason: str  # losses, voluntary, mutual_decision, breach, other
    exit_reason_details: Optional[str] = ""
    effective_date: str
    initiated_by: str  # franchisor or franchisee

class AssetHandover(BaseModel):
    kitchen_equipment: List[dict]
    furniture_fixtures: List[dict]
    utensils_machinery: List[dict]
    food_inventory: List[dict]
    packaging_materials: List[dict]
    other_assets: List[dict]
    condition_notes: Optional[str] = ""

class FinancialSettlement(BaseModel):
    working_capital_balance: float
    staff_salary_current: float
    shop_rental_current: float
    vendor_payments: float
    utility_bills: float
    other_dues: float
    settlement_notes: Optional[str] = ""

class DigitalSignature(BaseModel):
    signer_name: str
    signer_role: str  # franchisor or franchisee
    signer_designation: str
    signature_date: str
    ip_address: Optional[str] = ""

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

async def get_franchise(franchise_code: str):
    """Get franchise details"""
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code.upper()},
        {"_id": 0}
    )
    if not franchise:
        raise HTTPException(404, f"Franchise {franchise_code} not found")
    return franchise

# =======================================
# EXIT PROCESS ENDPOINTS
# =======================================

@router.post("/initiate")
async def initiate_exit(data: dict):
    """Initiate a franchise exit process"""
    token = data.get("token")
    session = await check_access(token)
    
    # Validate required fields
    required_fields = ["franchise_code", "exit_reason", "effective_date"]
    missing_fields = [f for f in required_fields if not data.get(f)]
    if missing_fields:
        raise HTTPException(422, f"Missing required fields: {', '.join(missing_fields)}")
    
    try:
        exit_data = ExitInitiation(**data)
    except Exception as e:
        raise HTTPException(422, f"Invalid data: {str(e)}")
    
    franchise = await get_franchise(exit_data.franchise_code)
    
    # Check if exit already in progress
    existing_exit = await db.franchise_exits.find_one({
        "franchise_code": exit_data.franchise_code.upper(),
        "status": {"$in": ["initiated", "in_progress", "pending_signatures"]}
    })
    
    if existing_exit:
        raise HTTPException(400, "An exit process is already in progress for this franchise")
    
    # Create exit record
    exit_record = {
        "exit_id": f"EXIT-{exit_data.franchise_code.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "franchise_code": exit_data.franchise_code.upper(),
        "franchise_name": franchise.get("franchise_name", ""),
        "legal_entity_name": franchise.get("legal_entity_name", ""),
        "exit_reason": exit_data.exit_reason,
        "exit_reason_details": exit_data.exit_reason_details,
        "effective_date": exit_data.effective_date,
        "initiated_by": exit_data.initiated_by,
        "initiated_by_user": session.get("managerName", ""),
        "initiated_at": datetime.now(timezone.utc).isoformat(),
        "status": "initiated",
        "steps_completed": {
            "exit_agreement": False,
            "asset_handover": False,
            "financial_settlement": False,
            "compliance_confirmation": False,
            "exit_certificate": False
        },
        "signatures": {
            "franchisor": None,
            "franchisee": None
        },
        "asset_handover": None,
        "financial_settlement": None,
        "compliance_checklist": {
            "no_pending_payments": False,
            "brand_assets_transferred": False,
            "financial_report_signed": False,
            "handover_report_signed": False
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.franchise_exits.insert_one(exit_record)
    
    # Log audit
    await db.franchise_audit.insert_one({
        "franchise_code": exit_data.franchise_code.upper(),
        "action": "EXIT_INITIATED",
        "user": session.get("managerName", ""),
        "details": {
            "exit_id": exit_record["exit_id"],
            "exit_reason": exit_data.exit_reason,
            "effective_date": exit_data.effective_date
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Exit initiated for {exit_data.franchise_code} by {session.get('managerName')}")
    
    return {
        "success": True,
        "message": "Franchise exit process initiated successfully",
        "exit_id": exit_record["exit_id"]
    }

@router.post("/list")
async def list_exits(data: dict):
    """List all franchise exits"""
    token = data.get("token")
    session = await check_access(token)
    
    status_filter = data.get("status")  # initiated, in_progress, completed, cancelled
    franchise_code = data.get("franchise_code")
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    if franchise_code:
        query["franchise_code"] = franchise_code.upper()
    
    exits = await db.franchise_exits.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return {
        "success": True,
        "exits": exits,
        "total": len(exits)
    }

@router.post("/get/{exit_id}")
async def get_exit_details(exit_id: str, data: dict):
    """Get detailed exit information"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one(
        {"exit_id": exit_id},
        {"_id": 0}
    )
    
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    # Get franchise details
    franchise = await db.franchises.find_one(
        {"franchise_code": exit_record["franchise_code"]},
        {"_id": 0}
    )
    
    return {
        "success": True,
        "exit": exit_record,
        "franchise": franchise
    }

@router.post("/update-asset-handover/{exit_id}")
async def update_asset_handover(exit_id: str, data: dict):
    """Update asset handover details"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    asset_data = {
        "kitchen_equipment": data.get("kitchen_equipment", []),
        "furniture_fixtures": data.get("furniture_fixtures", []),
        "utensils_machinery": data.get("utensils_machinery", []),
        "food_inventory": data.get("food_inventory", []),
        "packaging_materials": data.get("packaging_materials", []),
        "other_assets": data.get("other_assets", []),
        "condition_notes": data.get("condition_notes", ""),
        "updated_by": session.get("managerName", ""),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {
            "$set": {
                "asset_handover": asset_data,
                "steps_completed.asset_handover": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "message": "Asset handover details updated"}

@router.post("/update-financial-settlement/{exit_id}")
async def update_financial_settlement(exit_id: str, data: dict):
    """Update financial settlement details"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    settlement_data = {
        "working_capital_balance": float(data.get("working_capital_balance", 0)),
        "staff_salary_current": float(data.get("staff_salary_current", 0)),
        "shop_rental_current": float(data.get("shop_rental_current", 0)),
        "vendor_payments": float(data.get("vendor_payments", 0)),
        "utility_bills": float(data.get("utility_bills", 0)),
        "other_dues": float(data.get("other_dues", 0)),
        "settlement_notes": data.get("settlement_notes", ""),
        "total_settlement": (
            float(data.get("working_capital_balance", 0)) -
            float(data.get("staff_salary_current", 0)) -
            float(data.get("shop_rental_current", 0)) -
            float(data.get("vendor_payments", 0)) -
            float(data.get("utility_bills", 0)) -
            float(data.get("other_dues", 0))
        ),
        "updated_by": session.get("managerName", ""),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {
            "$set": {
                "financial_settlement": settlement_data,
                "steps_completed.financial_settlement": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "message": "Financial settlement updated"}

@router.post("/update-compliance/{exit_id}")
async def update_compliance(exit_id: str, data: dict):
    """Update compliance checklist"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    compliance_data = {
        "no_pending_payments": data.get("no_pending_payments", False),
        "brand_assets_transferred": data.get("brand_assets_transferred", False),
        "financial_report_signed": data.get("financial_report_signed", False),
        "handover_report_signed": data.get("handover_report_signed", False)
    }
    
    all_complete = all(compliance_data.values())
    
    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {
            "$set": {
                "compliance_checklist": compliance_data,
                "steps_completed.compliance_confirmation": all_complete,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "message": "Compliance checklist updated"}

@router.post("/sign/{exit_id}")
async def add_signature(exit_id: str, data: dict):
    """Add digital signature to exit documents"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    signer_role = data.get("signer_role")  # franchisor or franchisee
    if signer_role not in ["franchisor", "franchisee"]:
        raise HTTPException(400, "Invalid signer role")
    
    signature = {
        "signer_name": data.get("signer_name"),
        "signer_role": signer_role,
        "signer_designation": data.get("signer_designation", ""),
        "signature_date": datetime.now(timezone.utc).isoformat(),
        "ip_address": data.get("ip_address", ""),
        "signed_by_user": session.get("managerName", "")
    }
    
    update_field = f"signatures.{signer_role}"
    
    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {
            "$set": {
                update_field: signature,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Check if both signatures are complete
    updated_exit = await db.franchise_exits.find_one({"exit_id": exit_id})
    if updated_exit["signatures"]["franchisor"] and updated_exit["signatures"]["franchisee"]:
        await db.franchise_exits.update_one(
            {"exit_id": exit_id},
            {"$set": {"steps_completed.exit_agreement": True}}
        )
    
    return {"success": True, "message": f"{signer_role.title()} signature recorded"}

@router.post("/complete/{exit_id}")
async def complete_exit(exit_id: str, data: dict):
    """Complete the exit process and generate certificate"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    # Verify all steps are complete
    steps = exit_record.get("steps_completed", {})
    required_steps = ["exit_agreement", "asset_handover", "financial_settlement", "compliance_confirmation"]
    
    incomplete_steps = [step for step in required_steps if not steps.get(step)]
    if incomplete_steps:
        raise HTTPException(400, f"Cannot complete exit. Incomplete steps: {', '.join(incomplete_steps)}")
    
    # Update status to completed
    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {
            "$set": {
                "status": "completed",
                "steps_completed.exit_certificate": True,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "completed_by": session.get("managerName", ""),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update franchise status
    await db.franchises.update_one(
        {"franchise_code": exit_record["franchise_code"]},
        {
            "$set": {
                "status": "closed",
                "closure_date": datetime.now(timezone.utc).isoformat(),
                "exit_id": exit_id
            }
        }
    )
    
    # Log audit
    await db.franchise_audit.insert_one({
        "franchise_code": exit_record["franchise_code"],
        "action": "EXIT_COMPLETED",
        "user": session.get("managerName", ""),
        "details": {"exit_id": exit_id},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "message": "Franchise exit completed successfully"}

@router.post("/cancel/{exit_id}")
async def cancel_exit(exit_id: str, data: dict):
    """Cancel an exit process"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    if exit_record["status"] == "completed":
        raise HTTPException(400, "Cannot cancel a completed exit")
    
    cancellation_reason = data.get("cancellation_reason", "")
    
    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {
            "$set": {
                "status": "cancelled",
                "cancellation_reason": cancellation_reason,
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "cancelled_by": session.get("managerName", ""),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"success": True, "message": "Exit process cancelled"}

# =======================================
# DOCUMENT GENERATION ENDPOINTS
# =======================================

@router.post("/generate-exit-agreement/{exit_id}")
async def generate_exit_agreement(exit_id: str, data: dict):
    """Generate Exit Agreement PDF"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id}, {"_id": 0})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    franchise = await get_franchise(exit_record["franchise_code"])
    
    try:
        from utils.exit_documents_generator import ExitAgreementGenerator
        
        generator = ExitAgreementGenerator(exit_record, franchise)
        pdf_content = generator.generate_exit_agreement()
        
        filename = f"Exit_Agreement_{exit_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Error generating exit agreement: {e}")
        raise HTTPException(500, f"Error generating document: {str(e)}")

@router.post("/generate-handover-report/{exit_id}")
async def generate_handover_report(exit_id: str, data: dict):
    """Generate Asset Handover Report PDF"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id}, {"_id": 0})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    if not exit_record.get("asset_handover"):
        raise HTTPException(400, "Asset handover details not submitted yet")
    
    franchise = await get_franchise(exit_record["franchise_code"])
    
    try:
        from utils.exit_documents_generator import ExitAgreementGenerator
        
        generator = ExitAgreementGenerator(exit_record, franchise)
        pdf_content = generator.generate_handover_report()
        
        filename = f"Asset_Handover_Report_{exit_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Error generating handover report: {e}")
        raise HTTPException(500, f"Error generating document: {str(e)}")

@router.post("/generate-settlement-sheet/{exit_id}")
async def generate_settlement_sheet(exit_id: str, data: dict):
    """Generate Financial Settlement Sheet PDF"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id}, {"_id": 0})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    if not exit_record.get("financial_settlement"):
        raise HTTPException(400, "Financial settlement details not submitted yet")
    
    franchise = await get_franchise(exit_record["franchise_code"])
    
    try:
        from utils.exit_documents_generator import ExitAgreementGenerator
        
        generator = ExitAgreementGenerator(exit_record, franchise)
        pdf_content = generator.generate_settlement_sheet()
        
        filename = f"Financial_Settlement_{exit_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Error generating settlement sheet: {e}")
        raise HTTPException(500, f"Error generating document: {str(e)}")

@router.post("/generate-exit-certificate/{exit_id}")
async def generate_exit_certificate(exit_id: str, data: dict):
    """Generate Exit Completion Certificate PDF"""
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id}, {"_id": 0})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    if exit_record["status"] != "completed":
        raise HTTPException(400, "Exit process not yet completed")
    
    franchise = await get_franchise(exit_record["franchise_code"])
    
    try:
        from utils.exit_documents_generator import ExitAgreementGenerator
        
        generator = ExitAgreementGenerator(exit_record, franchise)
        pdf_content = generator.generate_exit_certificate()
        
        filename = f"Exit_Certificate_{exit_id}.pdf"
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logger.error(f"Error generating exit certificate: {e}")
        raise HTTPException(500, f"Error generating document: {str(e)}")
