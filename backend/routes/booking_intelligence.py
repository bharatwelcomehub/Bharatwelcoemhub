# =======================================
# Booking Intelligence & Guest Conversion Module
# Operations → Booking Intelligence
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import logging
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookings", tags=["Booking Intelligence"])

# Get DB reference (will be set from main server)
db = None
verify_token = None
verify_token_async_func = None

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_verify_token_async(func):
    global verify_token_async_func
    verify_token_async_func = func

# =======================================
# CONSTANTS
# =======================================

TIME_SLOTS = [
    "8:00 AM - 9:00 AM",
    "9:00 AM - 10:00 AM",
    "10:00 AM - 11:00 AM",
    "11:00 AM - 12:00 PM",
    "12:00 PM - 1:00 PM",
    "1:00 PM - 2:00 PM",
    "2:00 PM - 3:00 PM",
    "5:00 PM - 6:00 PM",
    "6:00 PM - 7:00 PM",
    "7:00 PM - 8:00 PM",
    "8:00 PM - 9:00 PM",
    "9:00 PM - 10:00 PM"
]

GUEST_TYPES = ["New Entry", "Repeat", "Party Guest", "Group Guest"]

CELEBRATION_TYPES = [
    "None",
    "Birthday",
    "Anniversary",
    "Just Get-together",
    "Kitty",
    "Womens Meet",
    "Office Team",
    "Family",
    "Baby Shower / Godbharai",
    "Kids Party",
    "Engagement",
    "Wedding",
    "Corporate Event",
    "Other"
]

MENU_STATUS = ["Yes", "No", "Partially Decided"]

BOOKING_SOURCES = [
    "Phone Call",
    "Walk-in",
    "WhatsApp",
    "Instagram",
    "Reference",
    "Website",
    "Google",
    "Zomato",
    "Swiggy",
    "Other"
]

BOOKING_STATUS = [
    "Enquiry",
    "Confirmed",
    "Visited",
    "Cancelled",
    "No Show",
    "Repeat Visit",
    "Converted to Catering",
    "Lost Lead"
]

CATERING_STATUS = [
    "Lead",
    "Discussing",
    "Quotation Sent",
    "Confirmed",
    "Completed",
    "Lost"
]

# Center WhatsApp numbers
CENTER_CONTACTS = {
    "PB-HSR": "+91 85500 78515",
    "PB-SN": "+91 89710 49084",  # Ch. Sambhajinagar
    "PB-TH": "+91 89047 49084",  # Thane
    "PB-DV": "+91 96064 55433",  # Dombivli
    "PB-KH": "+91 99000 89803",  # Kharadi
    "PB-HW": "+91 96064 55434",  # Hinjawadi
    "PB-PERTH": "+61 401 832 922",  # Perth
    "PB-KL": "+91 87928 87442",  # Kalyan
}

# =======================================
# ACCESS CHECK
# =======================================

async def check_booking_access(token: str) -> dict:
    """Check if user has access to booking module"""
    # Try async verification first (checks MongoDB for persistence)
    if verify_token_async_func:
        session = await verify_token_async_func(token)
        if session:
            return session
    
    # Fallback to sync verification (in-memory only)
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    return session

# =======================================
# HELPER FUNCTIONS
# =======================================

def normalize_phone(phone: str) -> str:
    """Normalize phone number for consistent storage and lookup"""
    if not phone:
        return ""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    # If starts with 91 and is 12 digits, remove country code
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    # If starts with 0, remove it
    if len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    return digits

def generate_booking_id(center: str) -> str:
    """Generate unique booking ID"""
    import uuid
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    short_uuid = str(uuid.uuid4())[:4].upper()
    return f"BK-{center}-{timestamp}-{short_uuid}"

# =======================================
# WHATSAPP MESSAGE TEMPLATES
# =======================================

def get_confirmation_message(booking: dict) -> str:
    """Generate booking confirmation WhatsApp message"""
    guest_name = booking.get("guest_name", "Guest")
    center = booking.get("center", "")
    date = booking.get("date", "")
    time_slot = booking.get("time_slot", "")
    num_guests = booking.get("num_guests", "")
    celebration = booking.get("celebration_type", "None")
    
    msg = f"""🙏 *Namaskar {guest_name}!*

Thank you for choosing *Purnabramha {center}*

📅 *Booking Details:*
• Date: {date}
• Time: {time_slot}
• Guests: {num_guests} persons"""
    
    if celebration and celebration != "None":
        msg += f"\n• Occasion: {celebration} 🎉"
    
    msg += """

We look forward to serving you with authentic Maharashtrian hospitality!

_Jai Hind!_
*Team Purnabramha* 🇮🇳"""
    
    return msg

def get_reminder_message(booking: dict) -> str:
    """Generate reminder WhatsApp message"""
    guest_name = booking.get("guest_name", "Guest")
    center = booking.get("center", "")
    time_slot = booking.get("time_slot", "")
    
    return f"""🙏 *Namaskar {guest_name}!*

This is a gentle reminder for your booking today at *Purnabramha {center}* at *{time_slot}*.

We look forward to welcoming you!

_Jai Hind!_
*Team Purnabramha* 🇮🇳"""

def get_thankyou_message(booking: dict) -> str:
    """Generate thank you WhatsApp message"""
    guest_name = booking.get("guest_name", "Guest")
    center = booking.get("center", "")
    
    return f"""🙏 *Namaskar {guest_name}!*

Thank you for visiting *Purnabramha {center}*!

It was our pleasure to host you. We hope you enjoyed the authentic Maharashtrian cuisine.

We look forward to serving you again! 🙏

_Jai Hind!_
*Team Purnabramha* 🇮🇳"""

def get_birthday_message(guest: dict) -> str:
    """Generate birthday greeting message"""
    guest_name = guest.get("name", "Guest")
    
    return f"""🎂 *Happy Birthday {guest_name}!* 🎉

*Purnabramha* wishes you a wonderful birthday filled with joy and happiness!

We would love to be part of your celebration. Book a table for your special day and make it memorable with authentic Maharashtrian cuisine!

🎁 Special celebration packages available!

_Jai Hind!_
*Team Purnabramha* 🇮🇳"""

def get_anniversary_message(guest: dict) -> str:
    """Generate anniversary greeting message"""
    guest_name = guest.get("name", "Guest")
    
    return f"""💑 *Happy Anniversary {guest_name}!* 🎉

*Purnabramha* wishes you a beautiful anniversary celebration!

Celebrate your special day with authentic Maharashtrian hospitality. Book a table and let us make it memorable!

_Jai Hind!_
*Team Purnabramha* 🇮🇳"""

def get_catering_followup_message(booking: dict) -> str:
    """Generate catering follow-up message"""
    guest_name = booking.get("guest_name", "Guest")
    
    return f"""🙏 *Namaskar {guest_name}!*

Thank you for discussing your catering requirement with *Purnabramha*.

We would be delighted to support your event with authentic Maharashtrian cuisine. Our team is ready to customize the menu as per your needs.

Please let us know if you need any clarification on the quotation.

_Jai Hind!_
*Team Purnabramha* 🇮🇳"""

# =======================================
# BOOKING CRUD ENDPOINTS
# =======================================

@router.post("/create")
async def create_booking(data: dict):
    """Create a new booking"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    # Validate required fields
    required = ["date", "guest_name", "phone", "time_slot", "num_guests"]
    for field in required:
        if not data.get(field):
            raise HTTPException(400, f"Missing required field: {field}")
    
    # Normalize phone number
    phone = normalize_phone(data.get("phone", ""))
    alt_phone = normalize_phone(data.get("alternate_phone", ""))
    
    # Get or determine center
    center = data.get("center") or session.get("center", "")
    if not center:
        raise HTTPException(400, "Center is required")
    
    # Generate booking ID
    booking_id = generate_booking_id(center)
    
    # Check if guest exists
    existing_guest = await db.guests.find_one({"phone": phone}, {"_id": 0})
    guest_type = data.get("guest_type", "New Entry")
    
    if existing_guest:
        guest_type = "Repeat"
        # Update guest's last visit info
        await db.guests.update_one(
            {"phone": phone},
            {"$set": {"last_booking_date": data.get("date"), "last_center": center},
             "$inc": {"total_bookings": 1}}
        )
    else:
        # Create new guest record
        new_guest = {
            "phone": phone,
            "name": data.get("guest_name", "").strip(),
            "alternate_phone": alt_phone,
            "email": data.get("email", ""),
            "date_of_birth": data.get("dob", ""),
            "anniversary_date": data.get("anniversary_date", ""),
            "kids_birthday": data.get("kids_birthday", ""),
            "family_notes": data.get("family_notes", ""),
            "preferences": data.get("preferences", ""),
            "first_visit_date": data.get("date"),
            "first_visit_center": center,
            "last_booking_date": data.get("date"),
            "last_center": center,
            "total_bookings": 1,
            "total_visits": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": session.get("managerName", "")
        }
        await db.guests.insert_one(new_guest)
    
    # Build booking document
    booking = {
        "booking_id": booking_id,
        "date": data.get("date"),
        "center": center,
        "guest_name": data.get("guest_name", "").strip(),
        "phone": phone,
        "alternate_phone": alt_phone,
        "time_slot": data.get("time_slot"),
        "num_guests": int(data.get("num_guests", 1)),
        "guest_type": guest_type,
        "celebration_type": data.get("celebration_type", "None"),
        "menu_decided": data.get("menu_decided", "No"),
        "menu_details": data.get("menu_details", ""),
        "is_catering": data.get("is_catering", False),
        "catering_details": data.get("catering_details", ""),
        "occasion_notes": data.get("occasion_notes", ""),
        "special_request": data.get("special_request", ""),
        "booking_source": data.get("booking_source", "Phone Call"),
        "status": data.get("status", "Enquiry"),
        "remarks": data.get("remarks", ""),
        "handled_by": data.get("handled_by") or session.get("managerName", ""),
        "follow_up_required": data.get("follow_up_required", False),
        "follow_up_date": data.get("follow_up_date", ""),
        "follow_up_remark": data.get("follow_up_remark", ""),
        "whatsapp_sent": False,
        "whatsapp_history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": session.get("managerName", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": session.get("managerName", "")
    }
    
    await db.bookings.insert_one(booking)
    
    # If catering, also create catering lead
    if data.get("is_catering"):
        catering_lead = {
            "booking_id": booking_id,
            "guest_name": booking["guest_name"],
            "phone": phone,
            "center": center,
            "event_date": data.get("catering_event_date") or data.get("date"),
            "event_type": data.get("celebration_type", ""),
            "approx_guests": data.get("catering_guests") or data.get("num_guests"),
            "location": data.get("catering_location", ""),
            "budget": data.get("catering_budget", ""),
            "menu_requirement": data.get("catering_menu", ""),
            "status": "Lead",
            "quotation_sent": False,
            "notes": data.get("catering_details", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": session.get("managerName", "")
        }
        await db.catering_leads.insert_one(catering_lead)
    
    logger.info(f"Booking created: {booking_id} by {session.get('managerName')}")
    
    return {
        "success": True,
        "booking_id": booking_id,
        "message": f"Booking created successfully",
        "guest_type": guest_type,
        "is_repeat_guest": existing_guest is not None
    }

@router.post("/list")
async def list_bookings(data: dict):
    """List bookings with filters"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    # Build query
    query = {}
    
    # Date filter
    date_from = data.get("date_from")
    date_to = data.get("date_to")
    if date_from and date_to:
        query["date"] = {"$gte": date_from, "$lte": date_to}
    elif date_from:
        query["date"] = {"$gte": date_from}
    elif date_to:
        query["date"] = {"$lte": date_to}
    
    # Center filter - non-admin can only see their center
    center = data.get("center")
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if center and center != "all":
        query["center"] = center
    elif not is_super_admin and not is_admin:
        query["center"] = session.get("center", "")
    
    # Status filter
    status = data.get("status")
    if status and status != "all":
        query["status"] = status
    
    # Celebration filter
    celebration = data.get("celebration_type")
    if celebration and celebration != "all":
        query["celebration_type"] = celebration
    
    # Search by phone or name
    search = data.get("search")
    if search:
        search_phone = normalize_phone(search)
        query["$or"] = [
            {"phone": {"$regex": search_phone, "$options": "i"}},
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"booking_id": {"$regex": search, "$options": "i"}}
        ]
    
    # Fetch bookings
    bookings = await db.bookings.find(query, {"_id": 0}).sort("date", -1).limit(500).to_list(500)
    
    # Get counts
    total = await db.bookings.count_documents(query)
    
    return {
        "bookings": bookings,
        "total": total
    }

@router.post("/get/{booking_id}")
async def get_booking(booking_id: str, data: dict):
    """Get single booking details"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    # Get guest history
    guest_history = None
    if booking.get("phone"):
        guest = await db.guests.find_one({"phone": booking["phone"]}, {"_id": 0})
        if guest:
            # Get past bookings
            past_bookings = await db.bookings.find(
                {"phone": booking["phone"], "booking_id": {"$ne": booking_id}},
                {"_id": 0, "booking_id": 1, "date": 1, "center": 1, "status": 1, "celebration_type": 1, "num_guests": 1}
            ).sort("date", -1).limit(10).to_list(10)
            
            guest_history = {
                **guest,
                "past_bookings": past_bookings
            }
    
    return {
        "booking": booking,
        "guest_history": guest_history
    }

@router.post("/update/{booking_id}")
async def update_booking(booking_id: str, data: dict):
    """Update booking"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    existing = await db.bookings.find_one({"booking_id": booking_id})
    if not existing:
        raise HTTPException(404, "Booking not found")
    
    # Build update
    update_fields = {}
    updatable = [
        "date", "guest_name", "phone", "alternate_phone", "time_slot", "num_guests",
        "guest_type", "celebration_type", "menu_decided", "menu_details",
        "is_catering", "catering_details", "occasion_notes", "special_request",
        "booking_source", "status", "remarks", "handled_by",
        "follow_up_required", "follow_up_date", "follow_up_remark"
    ]
    
    for field in updatable:
        if field in data and data[field] is not None:
            if field == "phone":
                update_fields[field] = normalize_phone(data[field])
            elif field == "alternate_phone":
                update_fields[field] = normalize_phone(data[field])
            else:
                update_fields[field] = data[field]
    
    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_fields["updated_by"] = session.get("managerName", "")
        
        await db.bookings.update_one(
            {"booking_id": booking_id},
            {"$set": update_fields}
        )
    
    # Update guest visit count if status changed to Visited
    if data.get("status") == "Visited" and existing.get("status") != "Visited":
        phone = existing.get("phone")
        if phone:
            await db.guests.update_one(
                {"phone": phone},
                {"$inc": {"total_visits": 1}}
            )
    
    return {"success": True, "message": "Booking updated"}

@router.post("/delete/{booking_id}")
async def delete_booking(booking_id: str, data: dict):
    """Delete booking"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    # Only super admin can delete
    if not session.get("is_super_admin"):
        raise HTTPException(403, "Only Super Admin can delete bookings")
    
    result = await db.bookings.delete_one({"booking_id": booking_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Booking not found")
    
    return {"success": True, "message": "Booking deleted"}

# =======================================
# GUEST LOOKUP ENDPOINT
# =======================================

@router.post("/guest-lookup")
async def guest_lookup(data: dict):
    """Look up guest by phone number"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    phone = normalize_phone(data.get("phone", ""))
    if not phone or len(phone) < 10:
        return {"found": False, "guest": None, "history": []}
    
    guest = await db.guests.find_one({"phone": phone}, {"_id": 0})
    
    if not guest:
        return {"found": False, "guest": None, "history": []}
    
    # Get booking history
    history = await db.bookings.find(
        {"phone": phone},
        {"_id": 0}
    ).sort("date", -1).limit(20).to_list(20)
    
    # Calculate stats
    total_visits = sum(1 for b in history if b.get("status") == "Visited")
    celebrations = [b.get("celebration_type") for b in history if b.get("celebration_type") and b.get("celebration_type") != "None"]
    
    return {
        "found": True,
        "guest": guest,
        "history": history,
        "stats": {
            "total_bookings": len(history),
            "total_visits": total_visits,
            "celebrations": celebrations,
            "last_visit_center": guest.get("last_center"),
            "preferred_time_slots": list(set(b.get("time_slot") for b in history if b.get("time_slot")))[:3]
        }
    }

# =======================================
# WHATSAPP ENDPOINTS
# =======================================

@router.post("/send-whatsapp/{booking_id}")
async def send_whatsapp(booking_id: str, data: dict):
    """Send WhatsApp message for booking"""
    token = data.get("token")
    message_type = data.get("type", "confirmation")  # confirmation, reminder, thankyou, catering
    
    session = await check_booking_access(token)
    
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    # Generate message based on type
    if message_type == "confirmation":
        message = get_confirmation_message(booking)
    elif message_type == "reminder":
        message = get_reminder_message(booking)
    elif message_type == "thankyou":
        message = get_thankyou_message(booking)
    elif message_type == "catering":
        message = get_catering_followup_message(booking)
    else:
        message = get_confirmation_message(booking)
    
    # Log the WhatsApp send (MOCKED for now)
    whatsapp_log = {
        "type": message_type,
        "message": message,
        "phone": booking.get("phone"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": session.get("managerName", ""),
        "status": "sent"  # In real implementation, this would be from API response
    }
    
    # Update booking with WhatsApp history
    await db.bookings.update_one(
        {"booking_id": booking_id},
        {
            "$set": {"whatsapp_sent": True},
            "$push": {"whatsapp_history": whatsapp_log}
        }
    )
    
    # Also log to separate collection for analytics
    await db.whatsapp_logs.insert_one({
        "booking_id": booking_id,
        "center": booking.get("center"),
        **whatsapp_log
    })
    
    logger.info(f"WhatsApp {message_type} sent for {booking_id}")
    
    return {
        "success": True,
        "message": f"WhatsApp {message_type} message sent",
        "preview": message,
        "note": "WhatsApp API integration pending - message logged for manual sending"
    }

@router.post("/preview-whatsapp/{booking_id}")
async def preview_whatsapp(booking_id: str, data: dict):
    """Preview WhatsApp message without sending"""
    token = data.get("token")
    message_type = data.get("type", "confirmation")
    
    session = await check_booking_access(token)
    
    booking = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    if message_type == "confirmation":
        message = get_confirmation_message(booking)
    elif message_type == "reminder":
        message = get_reminder_message(booking)
    elif message_type == "thankyou":
        message = get_thankyou_message(booking)
    elif message_type == "catering":
        message = get_catering_followup_message(booking)
    else:
        message = get_confirmation_message(booking)
    
    return {
        "message": message,
        "phone": booking.get("phone"),
        "type": message_type
    }

# =======================================
# CATERING ENDPOINTS
# =======================================

@router.post("/catering/list")
async def list_catering_leads(data: dict):
    """List catering leads"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    query = {}
    
    center = data.get("center")
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if center and center != "all":
        query["center"] = center
    elif not is_super_admin and not is_admin:
        query["center"] = session.get("center", "")
    
    status = data.get("status")
    if status and status != "all":
        query["status"] = status
    
    leads = await db.catering_leads.find(query, {"_id": 0}).sort("event_date", -1).limit(200).to_list(200)
    
    return {"leads": leads}

@router.post("/catering/update/{booking_id}")
async def update_catering(booking_id: str, data: dict):
    """Update catering lead status"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    update_fields = {}
    updatable = ["status", "quotation_sent", "notes", "event_date", "approx_guests", "budget", "menu_requirement"]
    
    for field in updatable:
        if field in data:
            update_fields[field] = data[field]
    
    if update_fields:
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.catering_leads.update_one(
            {"booking_id": booking_id},
            {"$set": update_fields}
        )
    
    return {"success": True}

# =======================================
# REMINDER ENDPOINTS
# =======================================

@router.post("/reminders/upcoming")
async def get_upcoming_reminders(data: dict):
    """Get upcoming birthday/anniversary reminders"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    today = datetime.now()
    today_mmdd = today.strftime("%m-%d")
    
    # Get dates for next 7 days
    upcoming_dates = []
    for i in range(8):
        d = today + timedelta(days=i)
        upcoming_dates.append(d.strftime("%m-%d"))
    
    # Find guests with birthdays
    guests = await db.guests.find({"phone": {"$exists": True}}, {"_id": 0}).to_list(5000)
    
    birthdays = []
    anniversaries = []
    kids_birthdays = []
    
    for guest in guests:
        dob = guest.get("date_of_birth", "")
        anniversary = guest.get("anniversary_date", "")
        kids_bday = guest.get("kids_birthday", "")
        
        if dob and len(dob) >= 5:
            dob_mmdd = dob[5:10]  # Extract MM-DD
            if dob_mmdd in upcoming_dates:
                days_until = upcoming_dates.index(dob_mmdd)
                birthdays.append({**guest, "days_until": days_until, "date": dob})
        
        if anniversary and len(anniversary) >= 5:
            ann_mmdd = anniversary[5:10]
            if ann_mmdd in upcoming_dates:
                days_until = upcoming_dates.index(ann_mmdd)
                anniversaries.append({**guest, "days_until": days_until, "date": anniversary})
        
        if kids_bday and len(kids_bday) >= 5:
            kids_mmdd = kids_bday[5:10]
            if kids_mmdd in upcoming_dates:
                days_until = upcoming_dates.index(kids_mmdd)
                kids_birthdays.append({**guest, "days_until": days_until, "date": kids_bday})
    
    # Sort by days until
    birthdays.sort(key=lambda x: x["days_until"])
    anniversaries.sort(key=lambda x: x["days_until"])
    kids_birthdays.sort(key=lambda x: x["days_until"])
    
    return {
        "birthdays": birthdays[:50],
        "anniversaries": anniversaries[:50],
        "kids_birthdays": kids_birthdays[:50],
        "today": today.strftime("%Y-%m-%d")
    }

@router.post("/reminders/send-greeting")
async def send_greeting(data: dict):
    """Send birthday/anniversary greeting"""
    token = data.get("token")
    phone = normalize_phone(data.get("phone", ""))
    greeting_type = data.get("type", "birthday")  # birthday, anniversary
    
    session = await check_booking_access(token)
    
    guest = await db.guests.find_one({"phone": phone}, {"_id": 0})
    if not guest:
        raise HTTPException(404, "Guest not found")
    
    if greeting_type == "birthday":
        message = get_birthday_message(guest)
    else:
        message = get_anniversary_message(guest)
    
    # Log greeting
    await db.whatsapp_logs.insert_one({
        "phone": phone,
        "type": f"{greeting_type}_greeting",
        "message": message,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "sent_by": session.get("managerName", ""),
        "status": "sent"
    })
    
    return {
        "success": True,
        "message": f"{greeting_type.capitalize()} greeting sent",
        "preview": message
    }

# =======================================
# FOLLOW-UP ENDPOINTS
# =======================================

@router.post("/followups/today")
async def get_todays_followups(data: dict):
    """Get bookings requiring follow-up today"""
    token = data.get("token")
    session = await check_booking_access(token)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    query = {
        "follow_up_required": True,
        "follow_up_date": today
    }
    
    if not session.get("is_super_admin") and not session.get("is_admin"):
        query["center"] = session.get("center", "")
    
    followups = await db.bookings.find(query, {"_id": 0}).to_list(100)
    
    return {"followups": followups, "count": len(followups)}

# =======================================
# DASHBOARD / ANALYTICS ENDPOINTS
# =======================================

@router.post("/dashboard/stats")
async def get_dashboard_stats(data: dict):
    """Get booking dashboard statistics"""
    token = data.get("token")
    period = data.get("period", "today")  # today, week, month
    center = data.get("center", "all")
    
    session = await check_booking_access(token)
    
    # Determine date range
    today = datetime.now()
    if period == "today":
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    elif period == "week":
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    else:  # month
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
    
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if center and center != "all":
        query["center"] = center
    elif not is_super_admin and not is_admin:
        query["center"] = session.get("center", "")
    
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(5000)
    
    # Calculate stats
    total = len(bookings)
    confirmed = sum(1 for b in bookings if b.get("status") == "Confirmed")
    visited = sum(1 for b in bookings if b.get("status") == "Visited")
    cancelled = sum(1 for b in bookings if b.get("status") in ["Cancelled", "No Show"])
    enquiries = sum(1 for b in bookings if b.get("status") == "Enquiry")
    
    # Celebration breakdown
    celebration_counts = {}
    for b in bookings:
        cel = b.get("celebration_type", "None")
        if cel and cel != "None":
            celebration_counts[cel] = celebration_counts.get(cel, 0) + 1
    
    # Guest type breakdown
    new_guests = sum(1 for b in bookings if b.get("guest_type") == "New Entry")
    repeat_guests = sum(1 for b in bookings if b.get("guest_type") == "Repeat")
    
    # Catering count
    catering = sum(1 for b in bookings if b.get("is_catering"))
    
    # Time slot distribution
    slot_counts = {}
    for b in bookings:
        slot = b.get("time_slot", "")
        if slot:
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    # Source distribution
    source_counts = {}
    for b in bookings:
        source = b.get("booking_source", "Other")
        source_counts[source] = source_counts.get(source, 0) + 1
    
    # Conversion metrics
    booking_to_visit = round((visited / confirmed * 100) if confirmed > 0 else 0, 1)
    enquiry_to_confirm = round((confirmed / (confirmed + enquiries) * 100) if (confirmed + enquiries) > 0 else 0, 1)
    
    return {
        "period": period,
        "date_range": {"start": start_date, "end": end_date},
        "summary": {
            "total_bookings": total,
            "enquiries": enquiries,
            "confirmed": confirmed,
            "visited": visited,
            "cancelled": cancelled,
            "catering_leads": catering,
            "new_guests": new_guests,
            "repeat_guests": repeat_guests
        },
        "conversion": {
            "enquiry_to_confirmed": enquiry_to_confirm,
            "booking_to_visit": booking_to_visit,
            "repeat_rate": round((repeat_guests / total * 100) if total > 0 else 0, 1)
        },
        "celebrations": celebration_counts,
        "time_slots": slot_counts,
        "sources": source_counts,
        "total_guests_expected": sum(b.get("num_guests", 0) for b in bookings if b.get("status") in ["Confirmed", "Enquiry"])
    }

@router.post("/dashboard/center-comparison")
async def get_center_comparison(data: dict):
    """Get center-wise booking comparison"""
    token = data.get("token")
    period = data.get("period", "month")
    
    session = await check_booking_access(token)
    
    if not session.get("is_super_admin") and not session.get("is_admin"):
        raise HTTPException(403, "Only admin can view center comparison")
    
    today = datetime.now()
    if period == "week":
        start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    else:
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    bookings = await db.bookings.find(
        {"date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0}
    ).to_list(10000)
    
    # Aggregate by center
    centers = {}
    for b in bookings:
        c = b.get("center", "Unknown")
        if c not in centers:
            centers[c] = {
                "center": c,
                "total": 0, "confirmed": 0, "visited": 0, "cancelled": 0,
                "celebrations": 0, "catering": 0, "new_guests": 0, "repeat_guests": 0
            }
        
        centers[c]["total"] += 1
        if b.get("status") == "Confirmed":
            centers[c]["confirmed"] += 1
        elif b.get("status") == "Visited":
            centers[c]["visited"] += 1
        elif b.get("status") in ["Cancelled", "No Show"]:
            centers[c]["cancelled"] += 1
        
        if b.get("celebration_type") and b.get("celebration_type") != "None":
            centers[c]["celebrations"] += 1
        if b.get("is_catering"):
            centers[c]["catering"] += 1
        if b.get("guest_type") == "New Entry":
            centers[c]["new_guests"] += 1
        elif b.get("guest_type") == "Repeat":
            centers[c]["repeat_guests"] += 1
    
    # Calculate conversion rates
    for c in centers.values():
        c["visit_rate"] = round((c["visited"] / c["confirmed"] * 100) if c["confirmed"] > 0 else 0, 1)
        c["repeat_rate"] = round((c["repeat_guests"] / c["total"] * 100) if c["total"] > 0 else 0, 1)
    
    return {
        "centers": sorted(centers.values(), key=lambda x: x["total"], reverse=True),
        "period": period
    }

@router.post("/dashboard/trends")
async def get_booking_trends(data: dict):
    """Get booking trends over time"""
    token = data.get("token")
    center = data.get("center", "all")
    days = data.get("days", 30)
    
    session = await check_booking_access(token)
    
    today = datetime.now()
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    
    query = {"date": {"$gte": start_date}}
    
    is_super_admin = session.get("is_super_admin", False)
    is_admin = session.get("is_admin", False)
    
    if center and center != "all":
        query["center"] = center
    elif not is_super_admin and not is_admin:
        query["center"] = session.get("center", "")
    
    bookings = await db.bookings.find(query, {"_id": 0}).to_list(10000)
    
    # Group by date
    daily = {}
    for b in bookings:
        date = b.get("date", "")
        if date not in daily:
            daily[date] = {"date": date, "bookings": 0, "confirmed": 0, "visited": 0, "guests": 0}
        daily[date]["bookings"] += 1
        if b.get("status") == "Confirmed":
            daily[date]["confirmed"] += 1
        elif b.get("status") == "Visited":
            daily[date]["visited"] += 1
        daily[date]["guests"] += b.get("num_guests", 0)
    
    trends = sorted(daily.values(), key=lambda x: x["date"])
    
    return {"trends": trends}

# =======================================
# CONSTANTS ENDPOINTS
# =======================================

@router.get("/constants")
async def get_constants():
    """Get all booking form constants"""
    return {
        "time_slots": TIME_SLOTS,
        "guest_types": GUEST_TYPES,
        "celebration_types": CELEBRATION_TYPES,
        "menu_status": MENU_STATUS,
        "booking_sources": BOOKING_SOURCES,
        "booking_status": BOOKING_STATUS,
        "catering_status": CATERING_STATUS,
        "center_contacts": CENTER_CONTACTS
    }
