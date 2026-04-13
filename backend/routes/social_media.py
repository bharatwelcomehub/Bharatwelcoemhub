# =======================================
# Social Media Planning & Content Tracker
# =======================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social-media", tags=["Social Media Planner"])

db = None
verify_token = None
has_admin_access = None
upload_fn = None  # Object storage upload function

def set_db(database):
    global db
    db = database

def set_verify_token(func):
    global verify_token
    verify_token = func

def set_has_admin_access(func):
    global has_admin_access
    has_admin_access = func

def set_upload_fn(func):
    global upload_fn
    upload_fn = func

CONTENT_TYPES = ["Video Post", "Reel", "Static Post", "Story", "Banner / Campaign", "Festival Campaign", "Monthly Plan", "Quarterly Plan", "Half-Yearly Plan", "Yearly Plan"]
PLATFORMS = ["Instagram", "Facebook", "Google Business", "YouTube", "Other"]
STATUSES = ["Planned", "In Progress", "Ready", "Posted", "Cancelled"]
CAMPAIGN_CATEGORIES = ["Daily", "Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Festival", "Special Promotion"]

def _now():
    return datetime.now(timezone.utc).isoformat()


@router.post("/constants")
async def get_constants(data: dict):
    """Return dropdown constants for the UI."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    return {
        "content_types": CONTENT_TYPES,
        "platforms": PLATFORMS,
        "statuses": STATUSES,
        "campaign_categories": CAMPAIGN_CATEGORIES,
    }


@router.post("/list")
async def list_posts(data: dict):
    """List social media posts with filters."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    is_admin = has_admin_access(session)
    query = {}

    # Role-based access
    if not is_admin:
        # Franchise owner or manager: own center only
        user_center = session.get("center", "")
        # Check if user has a linked franchise
        franchise = await db.franchises.find_one(
            {"$or": [{"owners": session.get("mobile")}, {"center_code": user_center}]},
            {"_id": 0, "center_code": 1}
        )
        if franchise:
            query["center"] = franchise.get("center_code", user_center)
        else:
            query["center"] = user_center

    # Admin filters
    if is_admin and data.get("center"):
        query["center"] = data["center"].upper()
    if data.get("status"):
        query["status"] = data["status"]
    if data.get("content_type"):
        query["content_type"] = data["content_type"]
    if data.get("platform"):
        query["platform"] = data["platform"]
    if data.get("campaign_category"):
        query["campaign_category"] = data["campaign_category"]
    if data.get("month"):
        query["$or"] = [
            {"post_date": {"$regex": f"^{data['month']}"}},
            {"planned_date": {"$regex": f"^{data['month']}"}},
        ]

    posts = await db.social_media_posts.find(query, {"_id": 0}).sort("planned_date", -1).to_list(2000)
    return {"posts": posts, "count": len(posts)}


@router.post("/save")
async def save_post(data: dict):
    """Create or update a social media post (Admin only)."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    if not has_admin_access(session):
        raise HTTPException(403, "Only Admin can manage social media posts")

    post_id = data.get("post_id", "")
    post_data = {
        "center": (data.get("center") or "").upper(),
        "content_type": data.get("content_type", ""),
        "platform": data.get("platform", ""),
        "post_title": data.get("post_title", ""),
        "caption": data.get("caption", ""),
        "hashtags": data.get("hashtags", ""),
        "creative_url": data.get("creative_url", ""),
        "video_url": data.get("video_url", ""),
        "thumbnail_url": data.get("thumbnail_url", ""),
        "post_date": data.get("post_date", ""),
        "planned_date": data.get("planned_date", ""),
        "status": data.get("status", "Planned"),
        "campaign_category": data.get("campaign_category", ""),
        "remarks": data.get("remarks", ""),
        "updatedAt": _now(),
        "updatedBy": session.get("managerName", session.get("mobile", "")),
    }

    if post_id:
        result = await db.social_media_posts.update_one(
            {"post_id": post_id}, {"$set": post_data}
        )
        if result.matched_count == 0:
            raise HTTPException(404, "Post not found")
        return {"success": True, "message": "Post updated", "post_id": post_id}
    else:
        post_id = f"SM-{str(uuid.uuid4())[:8].upper()}"
        post_data["post_id"] = post_id
        post_data["createdAt"] = _now()
        post_data["createdBy"] = session.get("managerName", session.get("mobile", ""))
        await db.social_media_posts.insert_one(post_data)
        return {"success": True, "message": "Post created", "post_id": post_id}


@router.post("/delete")
async def delete_post(data: dict):
    """Delete a social media post (Admin only)."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")
    if not has_admin_access(session):
        raise HTTPException(403, "Only Admin can delete posts")
    post_id = data.get("post_id")
    result = await db.social_media_posts.delete_one({"post_id": post_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Post not found")
    return {"success": True, "message": "Post deleted"}


@router.post("/upload-creative")
async def upload_creative(
    token: str = Form(...),
    post_id: str = Form(...),
    file_type: str = Form("creative"),
    file: UploadFile = File(...)
):
    """Upload a creative/video/thumbnail for a social media post."""
    session = verify_token(token)
    if not session or not has_admin_access(session):
        raise HTTPException(403, "Only Admin can upload creatives")

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "File must be under 50MB")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    path = f"purnabramha/social_media/{post_id}/{file_type}.{ext}"

    try:
        url = upload_fn(path, content, file.content_type)
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

    # Update post with file URL
    url_field = f"{file_type}_url"
    await db.social_media_posts.update_one(
        {"post_id": post_id},
        {"$set": {url_field: url, "updatedAt": _now()}}
    )
    return {"success": True, "url": url, "file_type": file_type}


@router.post("/dashboard")
async def social_media_dashboard(data: dict):
    """Get dashboard widgets data."""
    session = verify_token(data.get("token"))
    if not session:
        raise HTTPException(401, "Invalid token")

    is_admin = has_admin_access(session)
    query = {}
    if not is_admin:
        user_center = session.get("center", "")
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

    all_posts = await db.social_media_posts.find(query, {"_id": 0}).to_list(5000)

    # Status counts
    status_counts = {}
    for p in all_posts:
        st = p.get("status", "Planned")
        status_counts[st] = status_counts.get(st, 0) + 1

    # Platform counts
    platform_counts = {}
    for p in all_posts:
        pl = p.get("platform", "Other")
        platform_counts[pl] = platform_counts.get(pl, 0) + 1

    # Campaign category counts
    campaign_counts = {}
    for p in all_posts:
        cc = p.get("campaign_category", "")
        if cc:
            campaign_counts[cc] = campaign_counts.get(cc, 0) + 1

    # Upcoming posts (planned or in progress, future date)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    upcoming = [p for p in all_posts if p.get("status") in ("Planned", "In Progress", "Ready") and (p.get("planned_date", "") >= today or not p.get("planned_date"))]
    upcoming.sort(key=lambda x: x.get("planned_date", "9999"))

    # Posted vs planned ratio
    posted = status_counts.get("Posted", 0)
    planned = status_counts.get("Planned", 0) + status_counts.get("In Progress", 0) + status_counts.get("Ready", 0)

    return {
        "total_posts": len(all_posts),
        "status_counts": status_counts,
        "platform_counts": platform_counts,
        "campaign_counts": campaign_counts,
        "upcoming": upcoming[:15],
        "posted_count": posted,
        "planned_count": planned,
    }
