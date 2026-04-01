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
            "franchisee": None,
            "franchisor_signatories": [],
            "exit_manager": None,
            "franchisee_directors": []
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
    """List all franchise exits. Franchise owners only see their own."""
    token = data.get("token")
    session = await check_access(token)
    
    status_filter = data.get("status")  # initiated, in_progress, completed, cancelled
    franchise_code = data.get("franchise_code")
    
    # RBAC: If franchise_owner, restrict to their own franchise
    is_franchise_owner = session.get("role_key") == "franchise_owner"
    if is_franchise_owner:
        # Find their franchise code from their center
        owner_center = session.get("franchise_center") or session.get("center", "")
        if owner_center:
            # Look up franchise_code from franchise record linked to this center
            franchise = await db.franchises.find_one(
                {"$or": [{"center": owner_center}, {"centers_mapped": owner_center}]},
                {"_id": 0, "franchise_code": 1}
            )
            if franchise:
                franchise_code = franchise["franchise_code"]
            else:
                # Also check centers collection for franchise_code
                center_doc = await db.centers.find_one(
                    {"code": owner_center, "franchise_code": {"$exists": True, "$ne": ""}},
                    {"_id": 0, "franchise_code": 1}
                )
                if center_doc:
                    franchise_code = center_doc["franchise_code"]
                else:
                    return {"success": True, "exits": [], "total": 0}
        else:
            return {"success": True, "exits": [], "total": 0}
    
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
    """Add digital signature(s) to exit documents.
    Supports: franchisor_signatories (Sandeep/Jayanti), exit_manager, franchisee_directors.
    Also backward-compatible with old franchisor/franchisee roles.
    """
    token = data.get("token")
    session = await check_access(token)
    
    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")
    
    signer_type = data.get("signer_type", data.get("signer_role", ""))
    now = datetime.now(timezone.utc).isoformat()
    updates = {"updated_at": now}

    # --- FRANCHISOR SIGNATORIES (Sandeep / Jayanti or both) ---
    if signer_type == "franchisor_signatories":
        selected = data.get("selected_signatories", [])  # list of names
        signatories = []
        for name in selected:
            signatories.append({
                "signer_name": name,
                "signer_designation": "Director",
                "signature_date": now,
                "signed": True,
                "signed_by_user": session.get("managerName", "")
            })
        updates["signatures.franchisor_signatories"] = signatories
        # Backward compat: set franchisor to first signatory
        if signatories:
            updates["signatures.franchisor"] = signatories[0]

    # --- EXIT MANAGER ---
    elif signer_type == "exit_manager":
        updates["signatures.exit_manager"] = {
            "signer_name": data.get("signer_name", ""),
            "signer_role": "Exit Manager (Franchisor Side)",
            "signer_designation": data.get("signer_designation", "Exit Manager"),
            "signature_date": now,
            "signed": True,
            "signed_by_user": session.get("managerName", "")
        }

    # --- FRANCHISEE DIRECTORS (auto-pulled from franchise mgmt) ---
    elif signer_type == "franchisee_directors":
        directors_list = data.get("directors", [])
        dir_sigs = []
        for d in directors_list:
            dir_sigs.append({
                "signer_name": d.get("name", ""),
                "signer_designation": d.get("designation", "Director"),
                "signature_date": now,
                "signed": True,
                "signed_by_user": session.get("managerName", "")
            })
        updates["signatures.franchisee_directors"] = dir_sigs
        # Backward compat: set franchisee to first director
        if dir_sigs:
            updates["signatures.franchisee"] = {
                **dir_sigs[0],
                "signer_role": "franchisee"
            }

    # --- BACKWARD COMPATIBLE: old franchisor/franchisee single sign ---
    elif signer_type in ["franchisor", "franchisee"]:
        signature = {
            "signer_name": data.get("signer_name"),
            "signer_role": signer_type,
            "signer_designation": data.get("signer_designation", ""),
            "signature_date": now,
            "ip_address": data.get("ip_address", ""),
            "signed_by_user": session.get("managerName", "")
        }
        updates[f"signatures.{signer_type}"] = signature
    else:
        raise HTTPException(400, "Invalid signer_type. Use: franchisor_signatories, exit_manager, franchisee_directors")

    await db.franchise_exits.update_one(
        {"exit_id": exit_id},
        {"$set": updates}
    )
    
    # Check if all signature sections are complete
    updated_exit = await db.franchise_exits.find_one({"exit_id": exit_id})
    sigs = updated_exit.get("signatures", {})
    has_franchisor = bool(sigs.get("franchisor_signatories")) or bool(sigs.get("franchisor"))
    has_franchisee = bool(sigs.get("franchisee_directors")) or bool(sigs.get("franchisee"))
    
    if has_franchisor and has_franchisee:
        await db.franchise_exits.update_one(
            {"exit_id": exit_id},
            {"$set": {"steps_completed.exit_agreement": True}}
        )
    
    return {"success": True, "message": "Signature(s) recorded successfully"}


@router.get("/franchise-directors/{franchise_code}")
async def get_franchise_directors(franchise_code: str):
    """Get directors list from franchise management for auto-populating signatures"""
    franchise = await db.franchises.find_one(
        {"franchise_code": franchise_code},
        {"_id": 0, "directors": 1, "franchise_name": 1, "legal_entity_name": 1}
    )
    if not franchise:
        return {"directors": [], "franchise_name": "", "legal_entity_name": ""}
    
    return {
        "directors": franchise.get("directors", []),
        "franchise_name": franchise.get("franchise_name", ""),
        "legal_entity_name": franchise.get("legal_entity_name", "")
    }


async def _migrate_exit_signatures(exit_record):
    """Internal helper: migrate a single exit record to the new signature structure.
    Pulls directors from franchise management and converts old format to new."""
    exit_id = exit_record["exit_id"]
    franchise_code = exit_record.get("franchise_code", "")
    sigs = exit_record.get("signatures", {})
    now = datetime.now(timezone.utc).isoformat()
    updates = {"updated_at": now}

    # 1. FRANCHISOR SIGNATORIES — convert old franchisor to signatories array
    if not sigs.get("franchisor_signatories"):
        old_franchisor = sigs.get("franchisor")
        if old_franchisor:
            updates["signatures.franchisor_signatories"] = [{
                "signer_name": old_franchisor.get("signer_name", ""),
                "signer_designation": old_franchisor.get("signer_designation", "Director"),
                "signature_date": old_franchisor.get("signature_date", now),
                "signed": True,
                "signed_by_user": old_franchisor.get("signed_by_user", "")
            }]

    # 2. EXIT MANAGER — use initiated_by_user if not already set
    if not sigs.get("exit_manager"):
        manager_name = exit_record.get("initiated_by_user", "")
        if manager_name:
            updates["signatures.exit_manager"] = {
                "signer_name": manager_name,
                "signer_role": "Exit Manager (Franchisor Side)",
                "signer_designation": "Exit Manager",
                "signature_date": now,
                "signed": True,
                "signed_by_user": manager_name
            }

    # 3. FRANCHISEE DIRECTORS — pull from franchise management
    if not sigs.get("franchisee_directors"):
        franchise = await db.franchises.find_one(
            {"franchise_code": franchise_code},
            {"_id": 0, "directors": 1}
        )
        directors = franchise.get("directors", []) if franchise else []
        if directors:
            dir_sigs = []
            for d in directors:
                dir_sigs.append({
                    "signer_name": d.get("name", ""),
                    "signer_designation": d.get("designation", "Director"),
                    "signature_date": now,
                    "signed": True,
                    "signed_by_user": "Auto-populated from Franchise Management"
                })
            updates["signatures.franchisee_directors"] = dir_sigs
            # Also set backward-compat franchisee field if empty
            if not sigs.get("franchisee"):
                updates["signatures.franchisee"] = {
                    **dir_sigs[0],
                    "signer_role": "franchisee"
                }

    # Ensure new fields exist even if empty
    if "signatures.franchisor_signatories" not in updates and not sigs.get("franchisor_signatories"):
        updates["signatures.franchisor_signatories"] = []
    if "signatures.exit_manager" not in updates and not sigs.get("exit_manager"):
        updates["signatures.exit_manager"] = None
    if "signatures.franchisee_directors" not in updates and not sigs.get("franchisee_directors"):
        updates["signatures.franchisee_directors"] = []

    if updates:
        await db.franchise_exits.update_one(
            {"exit_id": exit_id},
            {"$set": updates}
        )

    return updates


@router.post("/migrate-signatures/{exit_id}")
async def migrate_single_exit_signatures(exit_id: str, data: dict):
    """Migrate a single exit record to the new signature structure"""
    token = data.get("token")
    session = await check_access(token)

    exit_record = await db.franchise_exits.find_one({"exit_id": exit_id})
    if not exit_record:
        raise HTTPException(404, "Exit record not found")

    updates = await _migrate_exit_signatures(exit_record)
    return {
        "success": True,
        "exit_id": exit_id,
        "message": "Signatures migrated successfully",
        "fields_updated": len(updates)
    }


@router.post("/migrate-all-signatures")
async def migrate_all_exit_signatures(data: dict):
    """Migrate ALL existing exit records to the new signature structure.
    Does NOT recreate exits — only adds the new signature fields."""
    token = data.get("token")
    session = await check_access(token)

    all_exits = await db.franchise_exits.find({}, {"_id": 0}).to_list(1000)
    results = []

    for exit_record in all_exits:
        exit_id = exit_record["exit_id"]
        updates = await _migrate_exit_signatures(exit_record)
        results.append({
            "exit_id": exit_id,
            "franchise_code": exit_record.get("franchise_code", ""),
            "fields_updated": len(updates)
        })

    return {
        "success": True,
        "message": f"Migrated {len(results)} exit records",
        "results": results
    }

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
