# =======================================
# Authentication Routes
# OTP, Sessions, Token Management
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import random
import string
import secrets
import smtplib
from email.message import EmailMessage
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Authentication"])

# Database reference
db = None
CFG = {}
OTP_LEN = 6
OTP_TTL = 300

def set_db(database):
    global db
    db = database

def set_config(config: dict, otp_len: int, otp_ttl: int):
    global CFG, OTP_LEN, OTP_TTL
    CFG = config
    OTP_LEN = otp_len
    OTP_TTL = otp_ttl

# =======================================
# MODELS
# =======================================

class OTPRequest(BaseModel):
    center: str
    mobile: str

class OTPVerify(BaseModel):
    center: str
    mobile: str
    otp: str

class TokenRequest(BaseModel):
    token: str

# =======================================
# SESSION HELPERS
# =======================================

async def save_session_to_db(key: str, session_data: dict):
    """Save session to MongoDB for persistence"""
    try:
        session_doc = {
            "key": key,
            **session_data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.sessions.update_one(
            {"key": key},
            {"$set": session_doc},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error saving session to DB: {e}")

async def get_session_from_db(key: str) -> Optional[dict]:
    """Get session from MongoDB"""
    try:
        session = await db.sessions.find_one({"key": key}, {"_id": 0})
        return session
    except Exception as e:
        logger.error(f"Error getting session from DB: {e}")
        return None

async def get_session_by_token(token: str) -> Optional[dict]:
    """Get session by token from MongoDB"""
    try:
        session = await db.sessions.find_one({"token": token}, {"_id": 0})
        return session
    except Exception as e:
        logger.error(f"Error getting session by token: {e}")
        return None

async def delete_session_from_db(key: str):
    """Delete session from MongoDB"""
    try:
        await db.sessions.delete_one({"key": key})
    except Exception as e:
        logger.error(f"Error deleting session from DB: {e}")

async def delete_session_by_token(token: str):
    """Delete session by token from MongoDB"""
    try:
        await db.sessions.delete_one({"token": token})
    except Exception as e:
        logger.error(f"Error deleting session by token: {e}")

# =======================================
# TOKEN HELPERS
# =======================================

def generate_otp():
    """Generate numeric OTP"""
    return ''.join(random.choices(string.digits, k=OTP_LEN))

def generate_token():
    return secrets.token_urlsafe(32)

async def verify_token_async(token: str) -> Optional[Dict]:
    """Verify token asynchronously"""
    if not token:
        return None
    
    # Get session from database
    session = await get_session_by_token(token)
    if not session:
        return None
    
    # Check if session is expired
    expires_at = session.get("expires")
    if expires_at:
        if isinstance(expires_at, str):
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > exp_dt:
                    await delete_session_by_token(token)
                    return None
            except:
                pass
    
    return session

def verify_token_sync(token: str) -> Optional[Dict]:
    """Sync wrapper - not recommended, use verify_token_async when possible"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None
        return loop.run_until_complete(verify_token_async(token))
    except:
        return None

def verify_token(token: str) -> Optional[Dict]:
    """Generic verify - returns None, use async version"""
    return None

def has_admin_access(session) -> bool:
    """Check if user has admin or super admin access"""
    if not session:
        return False
    if session.get("is_super_admin"):
        return True
    if session.get("is_admin"):
        return True
    return False

def has_all_centers_access(session) -> bool:
    """Check if user can access all centers"""
    if not session:
        return False
    if session.get("is_super_admin"):
        return True
    return session.get("roles", {}).get("view_all_centers", False)

# =======================================
# EMAIL HELPER
# =======================================

def send_otp_email(to_email: str, otp: str, manager_name: str, center: str) -> bool:
    """Send OTP via email"""
    email_cfg = CFG.get("email", {})
    if not email_cfg.get("enabled"):
        return False
    
    try:
        msg = EmailMessage()
        msg["Subject"] = f"Purnabramha Login OTP - {center}"
        msg["From"] = f"{email_cfg.get('from_name', 'Purnabramha')} <{email_cfg.get('from_email', '')}>"
        msg["To"] = to_email
        
        body = f"""
Dear {manager_name},

Your OTP for Purnabramha IntraPB login is: {otp}

Center: {center}
Valid for: 5 minutes

Do not share this OTP with anyone.

Regards,
Purnabramha Team
        """
        msg.set_content(body)
        
        with smtplib.SMTP(email_cfg.get("smtp_host", "smtp.gmail.com"), email_cfg.get("smtp_port", 587)) as server:
            server.starttls()
            server.login(email_cfg.get("smtp_user", ""), email_cfg.get("smtp_pass", ""))
            server.send_message(msg)
        
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        return False

# =======================================
# ENDPOINTS
# =======================================

@router.post("/send_otp")
async def send_otp(req: OTPRequest):
    """Send OTP to manager's mobile/email"""
    # Find the manager by center and mobile
    manager = await db.managers.find_one({
        "center": req.center,
        "mobile": req.mobile
    }, {"_id": 0})
    
    if not manager:
        raise HTTPException(404, "Manager not found for this center and mobile number")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in session with expiry
    session_key = f"{req.center}_{req.mobile}"
    expires = datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL)
    
    session_data = {
        "otp": otp,
        "center": req.center,
        "mobile": req.mobile,
        "managerName": manager.get("name", ""),
        "email": manager.get("email", ""),
        "expires": expires.isoformat(),
        "verified": False
    }
    
    await save_session_to_db(session_key, session_data)
    
    # Try to send OTP via email if configured
    email_sent = False
    if manager.get("email"):
        email_sent = send_otp_email(
            manager.get("email"),
            otp,
            manager.get("name", "Manager"),
            req.center
        )
    
    # For development, also log the OTP
    logger.info(f"OTP for {req.center}/{req.mobile}: {otp}")
    
    return {
        "success": True,
        "message": "OTP sent successfully",
        "email_sent": email_sent,
        "manager_name": manager.get("name", ""),
        # For development only - remove in production
        "dev_otp": otp if not email_sent else None
    }

@router.post("/verify_otp")
async def verify_otp(req: OTPVerify):
    """Verify OTP and create session"""
    session_key = f"{req.center}_{req.mobile}"
    
    # Get session from DB
    session = await get_session_from_db(session_key)
    
    if not session:
        raise HTTPException(400, "OTP not found or expired. Please request a new OTP.")
    
    # Check if expired
    expires = session.get("expires")
    if expires:
        try:
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp_dt:
                await delete_session_from_db(session_key)
                raise HTTPException(400, "OTP expired. Please request a new OTP.")
        except ValueError:
            pass
    
    # Verify OTP - allow bypass with 123456 for testing
    if req.otp != session.get("otp") and req.otp != "123456":
        raise HTTPException(400, "Invalid OTP")
    
    # Get manager details
    manager = await db.managers.find_one({
        "center": req.center,
        "mobile": req.mobile
    }, {"_id": 0})
    
    if not manager:
        raise HTTPException(404, "Manager not found")
    
    # Check if super admin (RBAC-driven, no center hardcoding)
    is_super_admin = manager.get("is_super_admin", False)
    is_admin = manager.get("is_admin", False) or is_super_admin
    
    # Generate token
    token = generate_token()
    
    # Session expiry - 8 hours for super admin, 4 hours for others
    session_hours = 8 if is_super_admin else 4
    new_expires = datetime.now(timezone.utc) + timedelta(hours=session_hours)
    
    # Create authenticated session
    auth_session = {
        "token": token,
        "center": req.center,
        "mobile": req.mobile,
        "managerName": manager.get("name", ""),
        "email": manager.get("email", ""),
        "is_super_admin": is_super_admin,
        "is_admin": is_admin,
        "role_key": manager.get("role_key", ""),
        "roles": manager.get("roles", {}),
        "franchise_center": manager.get("franchise_center", ""),
        "franchise_id": manager.get("franchise_id", ""),
        "expires": new_expires.isoformat(),
        "verified": True,
        "login_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Save authenticated session
    await save_session_to_db(f"auth_{token}", auth_session)
    
    # Also save with token as key for quick lookup
    await db.sessions.update_one(
        {"token": token},
        {"$set": auth_session},
        upsert=True
    )
    
    # Delete OTP session
    await delete_session_from_db(session_key)
    
    return {
        "success": True,
        "token": token,
        "center": req.center,
        "managerName": manager.get("name", ""),
        "is_super_admin": is_super_admin,
        "is_admin": is_admin,
        "role_key": manager.get("role_key", ""),
        "roles": manager.get("roles", {}),
        "franchise_center": manager.get("franchise_center", ""),
        "franchise_id": manager.get("franchise_id", ""),
        "expires_in_hours": session_hours
    }

@router.post("/logout")
async def logout(req: TokenRequest):
    """Logout and invalidate token"""
    if req.token:
        await delete_session_by_token(req.token)
    return {"success": True, "message": "Logged out successfully"}

@router.post("/verify_session")
async def verify_session(req: TokenRequest):
    """Verify if a session is still valid"""
    session = await verify_token_async(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired session")
    
    return {
        "success": True,
        "valid": True,
        "center": session.get("center"),
        "managerName": session.get("managerName"),
        "is_super_admin": session.get("is_super_admin", False),
        "is_admin": session.get("is_admin", False),
        "role_key": session.get("role_key", ""),
        "roles": session.get("roles", {}),
        "franchise_center": session.get("franchise_center", ""),
        "franchise_id": session.get("franchise_id", ""),
    }
