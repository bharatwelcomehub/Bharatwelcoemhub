# =======================================
# Employee Transfer Routes
# Transfer / Accept Shift Workflow
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transfers", tags=["Employee Transfers"])

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

# =======================================
# CONSTANTS
# =======================================

VALID_STATUSES = [
    "DRAFT", "PENDING_APPROVAL", "PENDING_ACCEPTANCE",
    "ACCEPTED", "REJECTED", "COMPLETED", "CANCELLED"
]

TRANSFER_TYPES = ["TEMPORARY", "PERMANENT"]

# =======================================
# PYDANTIC MODELS
# =======================================

class TransferRequest(BaseModel):
    token: str
    employee_name: str
    from_center: str
    to_center: str
    transfer_type: str  # TEMPORARY or PERMANENT
    start_date: str
    end_date: Optional[str] = None  # Required for TEMPORARY
    reason: str
    notes: Optional[str] = ""

class TransferActionRequest(BaseModel):
    token: str
    transfer_id: str
    action: str  # accept, reject, cancel
    notes: Optional[str] = ""

class TransferListRequest(BaseModel):
    token: str
    center: Optional[str] = None
    status: Optional[str] = None
    transfer_type: Optional[str] = None

class TransferHistoryRequest(BaseModel):
    token: str
    employee_name: Optional[str] = None
    center: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    transfer_type: Optional[str] = None
    status: Optional[str] = None

# =======================================
# HELPER FUNCTIONS
# =======================================

def make_serializable(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    result = {}
    for k, v in doc.items():
        if k == "_id":
            result["id"] = str(v)
        elif isinstance(v, ObjectId):
            result[k] = str(v)
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result

async def get_employee_by_name_center(name: str, center: str):
    """Find employee by name and center"""
    emp = await db.employees.find_one(
        {"name": name.upper(), "center": center.upper()},
        {"_id": 1, "name": 1, "center": 1, "designation": 1, "employee_id": 1,
         "home_center": 1, "current_operating_center": 1, "transfer_status": 1}
    )
    return emp

async def check_transfer_permission(session: dict) -> bool:
    """Check if user can initiate transfers — Admin, Super Admin, or Center Manager"""
    if session.get("is_super_admin") or session.get("is_admin"):
        return True
    # Center managers can initiate from their own center
    if session.get("center"):
        return True
    return False

async def get_active_transfer_for_employee(employee_name: str, center: str, date: str = None):
    """Get any active transfer affecting this employee on a given date"""
    query = {
        "employee_name": employee_name.upper(),
        "status": {"$in": ["ACCEPTED", "PENDING_ACCEPTANCE"]},
    }
    
    if date:
        query["start_date"] = {"$lte": date}
        query["$or"] = [
            {"end_date": {"$gte": date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    
    transfer = await db.transfer_requests.find_one(query, {"_id": 0, "id": {"$toString": "$_id"}})
    if transfer:
        transfer = make_serializable(
            await db.transfer_requests.find_one({"employee_name": employee_name.upper(), "status": {"$in": ["ACCEPTED", "PENDING_ACCEPTANCE"]}})
        )
    return transfer

# =======================================
# TRANSFER ENDPOINTS
# =======================================

@router.post("/create")
async def create_transfer(req: TransferRequest):
    """Create a new employee transfer request"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not await check_transfer_permission(session):
        raise HTTPException(403, "Not authorized to initiate transfers")
    
    # Validations
    from_center = req.from_center.upper().strip()
    to_center = req.to_center.upper().strip()
    transfer_type = req.transfer_type.upper().strip()
    
    if from_center == to_center:
        raise HTTPException(400, "Cannot transfer to the same center")
    
    if transfer_type not in TRANSFER_TYPES:
        raise HTTPException(400, f"Transfer type must be one of: {TRANSFER_TYPES}")
    
    if transfer_type == "TEMPORARY" and not req.end_date:
        raise HTTPException(400, "End date is required for temporary transfers")
    
    if req.end_date and req.start_date > req.end_date:
        raise HTTPException(400, "End date must be after start date")
    
    # Check employee exists in from_center
    emp = await get_employee_by_name_center(req.employee_name, from_center)
    if not emp:
        raise HTTPException(404, f"Employee '{req.employee_name}' not found in center {from_center}")
    
    # Check for duplicate active transfer
    existing = await db.transfer_requests.find_one({
        "employee_name": req.employee_name.upper(),
        "status": {"$in": ["DRAFT", "PENDING_APPROVAL", "PENDING_ACCEPTANCE", "ACCEPTED"]},
        "$or": [
            # Overlapping dates for temporary
            {"$and": [
                {"start_date": {"$lte": req.end_date or "9999-12-31"}},
                {"$or": [
                    {"end_date": {"$gte": req.start_date}},
                    {"end_date": None},
                    {"end_date": ""},
                    {"transfer_type": "PERMANENT"}
                ]}
            ]}
        ]
    })
    
    if existing:
        raise HTTPException(400, "An active transfer request already exists for this employee with overlapping dates")
    
    # Check destination center exists
    dest_center = await db.centers.find_one({"code": to_center})
    if not dest_center:
        raise HTTPException(404, f"Destination center '{to_center}' not found")
    
    # Determine initial status based on who is creating
    is_admin = session.get("is_super_admin") or session.get("is_admin")
    initial_status = "PENDING_ACCEPTANCE" if is_admin else "PENDING_ACCEPTANCE"
    
    transfer_doc = {
        "employee_name": req.employee_name.upper(),
        "employee_id": emp.get("employee_id") or str(emp.get("_id", "")),
        "home_center": emp.get("home_center") or from_center,
        "from_center": from_center,
        "to_center": to_center,
        "transfer_type": transfer_type,
        "start_date": req.start_date,
        "end_date": req.end_date if transfer_type == "TEMPORARY" else None,
        "status": initial_status,
        "reason": req.reason.strip(),
        "request_notes": req.notes or "",
        "action_notes": "",
        "requested_by": session.get("managerName", "Unknown"),
        "requested_by_center": session.get("center", ""),
        "approved_by": session.get("managerName", "") if is_admin else "",
        "accepted_by": "",
        "rejected_by": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.transfer_requests.insert_one(transfer_doc)
    transfer_id = str(result.inserted_id)
    
    # Create notification for destination center
    await db.transfer_notifications.insert_one({
        "transfer_id": transfer_id,
        "center": to_center,
        "type": "TRANSFER_REQUEST",
        "message": f"Transfer request: {req.employee_name} from {from_center} ({transfer_type})",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Also notify source center
    await db.transfer_notifications.insert_one({
        "transfer_id": transfer_id,
        "center": from_center,
        "type": "TRANSFER_INITIATED",
        "message": f"Transfer initiated: {req.employee_name} to {to_center} ({transfer_type})",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"Transfer created: {req.employee_name} from {from_center} to {to_center} ({transfer_type}) by {session.get('managerName')}")
    
    return {"success": True, "transfer_id": transfer_id, "status": initial_status, "message": "Transfer request created successfully"}


@router.post("/action")
async def transfer_action(req: TransferActionRequest):
    """Accept, reject, or cancel a transfer request"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    action = req.action.lower().strip()
    if action not in ["accept", "reject", "cancel"]:
        raise HTTPException(400, "Action must be: accept, reject, or cancel")
    
    # Find transfer
    try:
        transfer = await db.transfer_requests.find_one({"_id": ObjectId(req.transfer_id)})
    except Exception:
        raise HTTPException(400, "Invalid transfer ID")
    
    if not transfer:
        raise HTTPException(404, "Transfer request not found")
    
    user_center = session.get("center", "").upper()
    is_admin = session.get("is_super_admin") or session.get("is_admin")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if action == "accept":
        if transfer["status"] not in ["PENDING_ACCEPTANCE"]:
            raise HTTPException(400, f"Cannot accept transfer in status: {transfer['status']}")
        
        # Only destination center manager or admin can accept
        if not is_admin and user_center != transfer["to_center"]:
            raise HTTPException(403, "Only destination center manager or admin can accept transfers")
        
        # Update transfer status
        await db.transfer_requests.update_one(
            {"_id": ObjectId(req.transfer_id)},
            {"$set": {
                "status": "ACCEPTED",
                "accepted_by": session.get("managerName", "Unknown"),
                "action_notes": req.notes or "",
                "updated_at": now
            }}
        )
        
        # Update employee based on transfer type
        emp_name = transfer["employee_name"]
        from_center = transfer["from_center"]
        to_center = transfer["to_center"]
        
        if transfer["transfer_type"] == "PERMANENT":
            # Permanent: change employee center
            await db.employees.update_many(
                {"name": emp_name, "center": from_center},
                {"$set": {
                    "center": to_center,
                    "home_center": to_center,
                    "current_operating_center": to_center,
                    "transfer_status": "PERMANENTLY_TRANSFERRED",
                    "active_transfer_id": req.transfer_id,
                    "permanent_transfer_effective_date": transfer["start_date"],
                    "updated_at": now
                }}
            )
        else:
            # Temporary: update operating center, keep home center
            home = transfer.get("home_center") or from_center
            await db.employees.update_many(
                {"name": emp_name, "center": from_center},
                {"$set": {
                    "home_center": home,
                    "current_operating_center": to_center,
                    "transfer_status": "TEMPORARY_SHIFT",
                    "active_transfer_id": req.transfer_id,
                    "transfer_start_date": transfer["start_date"],
                    "transfer_end_date": transfer.get("end_date", ""),
                    "updated_at": now
                }}
            )
        
        # Notifications
        await db.transfer_notifications.insert_one({
            "transfer_id": req.transfer_id,
            "center": from_center,
            "type": "TRANSFER_ACCEPTED",
            "message": f"Transfer accepted: {emp_name} to {to_center} by {session.get('managerName')}",
            "read": False,
            "created_at": now
        })
        
        logger.info(f"Transfer accepted: {emp_name} {from_center}->{to_center} by {session.get('managerName')}")
        return {"success": True, "message": f"Transfer accepted. {emp_name} now assigned to {to_center}.", "status": "ACCEPTED"}
    
    elif action == "reject":
        if transfer["status"] not in ["PENDING_ACCEPTANCE", "PENDING_APPROVAL"]:
            raise HTTPException(400, f"Cannot reject transfer in status: {transfer['status']}")
        
        # Destination center manager or admin can reject
        if not is_admin and user_center != transfer["to_center"]:
            raise HTTPException(403, "Only destination center manager or admin can reject transfers")
        
        await db.transfer_requests.update_one(
            {"_id": ObjectId(req.transfer_id)},
            {"$set": {
                "status": "REJECTED",
                "rejected_by": session.get("managerName", "Unknown"),
                "action_notes": req.notes or "",
                "updated_at": now
            }}
        )
        
        # Notify source center
        await db.transfer_notifications.insert_one({
            "transfer_id": req.transfer_id,
            "center": transfer["from_center"],
            "type": "TRANSFER_REJECTED",
            "message": f"Transfer rejected: {transfer['employee_name']} to {transfer['to_center']}. Reason: {req.notes or 'No reason given'}",
            "read": False,
            "created_at": now
        })
        
        logger.info(f"Transfer rejected: {transfer['employee_name']} by {session.get('managerName')}")
        return {"success": True, "message": "Transfer rejected.", "status": "REJECTED"}
    
    elif action == "cancel":
        if transfer["status"] in ["COMPLETED", "CANCELLED"]:
            raise HTTPException(400, f"Cannot cancel transfer in status: {transfer['status']}")
        
        # Source center manager, admin, or requesting user can cancel
        if not is_admin and user_center != transfer["from_center"]:
            raise HTTPException(403, "Only source center manager or admin can cancel transfers")
        
        # If was already accepted, revert employee
        if transfer["status"] == "ACCEPTED":
            emp_name = transfer["employee_name"]
            home = transfer.get("home_center") or transfer["from_center"]
            
            if transfer["transfer_type"] == "PERMANENT":
                await db.employees.update_many(
                    {"name": emp_name, "center": transfer["to_center"]},
                    {"$set": {
                        "center": home,
                        "home_center": home,
                        "current_operating_center": home,
                        "transfer_status": "",
                        "active_transfer_id": "",
                        "updated_at": now
                    }}
                )
            else:
                await db.employees.update_many(
                    {"name": emp_name},
                    {"$set": {
                        "current_operating_center": home,
                        "transfer_status": "",
                        "active_transfer_id": "",
                        "transfer_start_date": "",
                        "transfer_end_date": "",
                        "updated_at": now
                    }}
                )
        
        await db.transfer_requests.update_one(
            {"_id": ObjectId(req.transfer_id)},
            {"$set": {
                "status": "CANCELLED",
                "action_notes": req.notes or "",
                "updated_at": now
            }}
        )
        
        logger.info(f"Transfer cancelled: {transfer['employee_name']} by {session.get('managerName')}")
        return {"success": True, "message": "Transfer cancelled.", "status": "CANCELLED"}


@router.post("/list")
async def list_transfers(req: TransferListRequest):
    """List transfer requests — incoming, outgoing, and active for a center"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    user_center = (req.center or session.get("center", "")).upper()
    is_admin = session.get("is_super_admin") or session.get("is_admin")
    
    # Build query based on filters
    base_query = {}
    if req.status:
        base_query["status"] = req.status.upper()
    if req.transfer_type:
        base_query["transfer_type"] = req.transfer_type.upper()
    
    if is_admin and not req.center:
        # Admin sees all
        incoming_q = {**base_query}
        outgoing_q = {**base_query}
        active_q = {"status": "ACCEPTED"}
    else:
        incoming_q = {**base_query, "to_center": user_center}
        outgoing_q = {**base_query, "from_center": user_center}
        active_q = {"status": "ACCEPTED", "$or": [{"from_center": user_center}, {"to_center": user_center}]}
    
    # Incoming requests
    incoming_raw = await db.transfer_requests.find(
        {**incoming_q, "status": {"$in": ["PENDING_ACCEPTANCE", "PENDING_APPROVAL"]}} if not req.status else incoming_q
    ).sort("created_at", -1).to_list(500)
    incoming = [make_serializable(t) for t in incoming_raw]
    
    # Outgoing requests
    outgoing_raw = await db.transfer_requests.find(outgoing_q).sort("created_at", -1).to_list(500)
    outgoing = [make_serializable(t) for t in outgoing_raw]
    
    # Active shifts (currently transferred employees)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    active_q_full = {
        **active_q,
        "start_date": {"$lte": today},
        "$or": [
            {"end_date": {"$gte": today}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }
    active_raw = await db.transfer_requests.find(active_q_full).sort("start_date", -1).to_list(500)
    active = [make_serializable(t) for t in active_raw]
    
    # Unread notifications count
    notif_count = await db.transfer_notifications.count_documents({
        "center": user_center, "read": False
    })
    
    return {
        "success": True,
        "incoming": incoming,
        "outgoing": outgoing,
        "active": active,
        "unread_notifications": notif_count
    }


@router.post("/notifications")
async def get_notifications(data: dict):
    """Get transfer notifications for a center"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = (data.get("center") or session.get("center", "")).upper()
    is_admin = session.get("is_super_admin") or session.get("is_admin")
    
    query = {} if is_admin else {"center": center}
    
    notifs_raw = await db.transfer_notifications.find(query).sort("created_at", -1).to_list(100)
    notifs = [make_serializable(n) for n in notifs_raw]
    
    return {"success": True, "notifications": notifs}


@router.post("/notifications/mark-read")
async def mark_notifications_read(data: dict):
    """Mark transfer notifications as read"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = (data.get("center") or session.get("center", "")).upper()
    
    await db.transfer_notifications.update_many(
        {"center": center, "read": False},
        {"$set": {"read": True}}
    )
    
    return {"success": True}


@router.post("/history")
async def transfer_history(req: TransferHistoryRequest):
    """Get complete transfer history with filters"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    query = {}
    
    if req.employee_name:
        query["employee_name"] = req.employee_name.upper()
    if req.center:
        query["$or"] = [{"from_center": req.center.upper()}, {"to_center": req.center.upper()}]
    if req.transfer_type:
        query["transfer_type"] = req.transfer_type.upper()
    if req.status:
        query["status"] = req.status.upper()
    if req.start_date:
        query["created_at"] = {"$gte": req.start_date}
    if req.end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = req.end_date + "T23:59:59"
        else:
            query["created_at"] = {"$lte": req.end_date + "T23:59:59"}
    
    # Non-admin can only see transfers related to their center
    if not (session.get("is_super_admin") or session.get("is_admin")):
        user_center = session.get("center", "").upper()
        center_filter = {"$or": [{"from_center": user_center}, {"to_center": user_center}]}
        if "$or" in query:
            query = {"$and": [query, center_filter]}
        else:
            query.update(center_filter)
    
    records_raw = await db.transfer_requests.find(query).sort("created_at", -1).to_list(1000)
    records = [make_serializable(r) for r in records_raw]
    
    return {"success": True, "history": records, "total": len(records)}


@router.post("/employee-status")
async def get_employee_transfer_status(data: dict):
    """Get transfer status for employees in a center (for attendance integration)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    center = data.get("center", "").upper()
    date = data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    
    # Get employees transferred INTO this center (active on this date)
    transferred_in = await db.transfer_requests.find({
        "to_center": center,
        "status": "ACCEPTED",
        "start_date": {"$lte": date},
        "$or": [
            {"end_date": {"$gte": date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }).to_list(500)
    
    # Get employees transferred OUT of this center (active on this date)
    transferred_out = await db.transfer_requests.find({
        "from_center": center,
        "status": "ACCEPTED",
        "start_date": {"$lte": date},
        "$or": [
            {"end_date": {"$gte": date}},
            {"end_date": None},
            {"end_date": ""},
            {"transfer_type": "PERMANENT"}
        ]
    }).to_list(500)
    
    # Get pending transfers
    pending = await db.transfer_requests.find({
        "$or": [{"from_center": center}, {"to_center": center}],
        "status": "PENDING_ACCEPTANCE"
    }).to_list(100)
    
    in_names = [make_serializable(t) for t in transferred_in]
    out_names = [make_serializable(t) for t in transferred_out]
    pending_list = [make_serializable(t) for t in pending]
    
    return {
        "success": True,
        "transferred_in": in_names,
        "transferred_out": out_names,
        "pending": pending_list,
        "date": date
    }


@router.post("/auto-complete-expired")
async def auto_complete_expired(data: dict):
    """Auto-complete expired temporary transfers (called on app startup or periodically)"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if not (session.get("is_super_admin") or session.get("is_admin")):
        raise HTTPException(403, "Only admin can trigger auto-complete")
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    
    # Find expired temporary transfers
    expired = await db.transfer_requests.find({
        "transfer_type": "TEMPORARY",
        "status": "ACCEPTED",
        "end_date": {"$lt": today}
    }).to_list(500)
    
    completed = 0
    for transfer in expired:
        emp_name = transfer["employee_name"]
        home = transfer.get("home_center") or transfer["from_center"]
        
        # Revert employee to home center
        await db.employees.update_many(
            {"name": emp_name},
            {"$set": {
                "current_operating_center": home,
                "transfer_status": "",
                "active_transfer_id": "",
                "transfer_start_date": "",
                "transfer_end_date": "",
                "updated_at": now
            }}
        )
        
        # Mark transfer as completed
        await db.transfer_requests.update_one(
            {"_id": transfer["_id"]},
            {"$set": {
                "status": "COMPLETED",
                "action_notes": f"Auto-completed: temporary transfer ended on {transfer['end_date']}",
                "updated_at": now
            }}
        )
        
        # Notification
        await db.transfer_notifications.insert_one({
            "transfer_id": str(transfer["_id"]),
            "center": home,
            "type": "TRANSFER_COMPLETED",
            "message": f"{emp_name} has returned from temporary shift at {transfer['to_center']}",
            "read": False,
            "created_at": now
        })
        
        await db.transfer_notifications.insert_one({
            "transfer_id": str(transfer["_id"]),
            "center": transfer["to_center"],
            "type": "TRANSFER_COMPLETED",
            "message": f"{emp_name}'s temporary shift has ended. Employee returned to {home}",
            "read": False,
            "created_at": now
        })
        
        completed += 1
        logger.info(f"Auto-completed transfer: {emp_name} returned to {home}")
    
    return {"success": True, "completed": completed}


@router.post("/reports/summary")
async def transfer_summary_report(data: dict):
    """Center-wise transfer in/out summary report"""
    token = data.get("token")
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    start_date = data.get("start_date", "2020-01-01")
    end_date = data.get("end_date", "2099-12-31")
    
    # Get all centers
    centers = await db.centers.find({"is_india_center": True}, {"_id": 0, "code": 1, "name": 1}).to_list(100)
    
    summary = []
    for c in centers:
        code = c["code"]
        
        transfers_in = await db.transfer_requests.count_documents({
            "to_center": code,
            "status": {"$in": ["ACCEPTED", "COMPLETED"]},
            "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"}
        })
        
        transfers_out = await db.transfer_requests.count_documents({
            "from_center": code,
            "status": {"$in": ["ACCEPTED", "COMPLETED"]},
            "created_at": {"$gte": start_date, "$lte": end_date + "T23:59:59"}
        })
        
        active_in = await db.transfer_requests.count_documents({
            "to_center": code, "status": "ACCEPTED"
        })
        
        active_out = await db.transfer_requests.count_documents({
            "from_center": code, "status": "ACCEPTED"
        })
        
        pending = await db.transfer_requests.count_documents({
            "to_center": code, "status": "PENDING_ACCEPTANCE"
        })
        
        summary.append({
            "center_code": code,
            "center_name": c.get("name", code),
            "total_transfers_in": transfers_in,
            "total_transfers_out": transfers_out,
            "active_transfers_in": active_in,
            "active_transfers_out": active_out,
            "pending_requests": pending
        })
    
    return {"success": True, "summary": summary}
