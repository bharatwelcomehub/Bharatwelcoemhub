from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Response, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import httpx
import json
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

JWT_SECRET = os.environ.get('JWT_SECRET', 'purnabramha-secret-key-2025')
JWT_ALGORITHM = 'HS256'

# Push notification config (basic structure for future Firebase integration)
PUSH_ENABLED = os.environ.get('PUSH_ENABLED', 'false').lower() == 'true'

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Get current user from JWT token or session cookie"""
    token = None
    
    # Try Authorization header first
    if credentials:
        token = credentials.credentials
    
    # Fallback to session_token cookie
    if not token:
        token = request.cookies.get('session_token')
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if it's a session token (from Google OAuth)
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if session:
        # Validate session expiry
        expires_at = session.get('expires_at')
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        return {"user_id": session['user_id'], "email": session.get('email', '')}
    
    # Try JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """Get current user if authenticated, otherwise return None"""
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    phone: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    city: str
    country: str
    address: str
    phone: str
    whatsapp: str
    google_review_link: Optional[str] = None
    is_active: bool = True
    # Center / booking fields (used by Table Booking page)
    center_id: Optional[str] = None  # e.g. "pb-hsr"; slug used by /api/center-timeslots
    display_name: Optional[str] = None  # e.g. "HSR Layout, Bangalore"
    state: Optional[str] = None
    currency: Optional[str] = None  # "INR" or "AUD"
    currency_symbol: Optional[str] = None  # "₹" or "$"
    services: List[str] = Field(default_factory=lambda: ["dine-in", "pickup", "tiffin", "catering", "unlimited-breakfast"])

class MenuItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str
    price: float
    price_inr: Optional[float] = None
    price_aud: Optional[float] = None
    image_url: Optional[str] = None
    is_veg: bool = True
    is_available: bool = True
    no_onion_garlic: bool = False
    fasting_friendly: bool = False

class HeroImage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    image_url: str
    description: Optional[str] = None
    is_active: bool = True
    order: int = 0

class Video(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    video_url: str
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    category: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CartItem(BaseModel):
    menu_item_id: str
    name: str
    price: float
    quantity: int

class PickupOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    location_id: str
    items: List[CartItem]
    total_amount: float
    pickup_time: str
    status: str = "pending"
    payment_status: str = "pending"
    payment_method: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PickupOrderCreate(BaseModel):
    location_id: str
    items: List[CartItem]
    pickup_time: str
    payment_method: str

class TableBooking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    location_id: str
    booking_date: str
    booking_time: str
    party_size: int
    special_requests: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TableBookingCreate(BaseModel):
    location_id: str
    booking_date: str
    booking_time: str
    party_size: int
    special_requests: Optional[str] = None

class TiffinSubscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    location_id: str
    plan_type: str
    delivery_address: str
    start_date: str
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TiffinSubscriptionCreate(BaseModel):
    location_id: str
    plan_type: str
    delivery_address: str
    start_date: str

class CateringRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    event_date: str
    event_type: str
    guest_count: int
    venue_address: str
    requirements: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CateringRequestCreate(BaseModel):
    event_date: str
    event_type: str
    guest_count: int
    venue_address: str
    requirements: str

@api_router.post("/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_data.model_dump()
    password = user_dict.pop('password')
    hashed = hash_password(password)
    
    user = User(**user_dict)
    doc = user.model_dump()
    doc['password'] = hashed
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    token = create_token(user.id, user.email)
    
    return {"token": token, "user": user.model_dump()}

@api_router.post("/auth/login", response_model=dict)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user_doc['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_doc.pop('password')
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    user = User(**user_doc)
    token = create_token(user.id, user.email)
    
    return {"token": token, "user": user.model_dump()}

@api_router.get("/auth/me")
async def get_me(request: Request, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**user_doc)

# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
@api_router.post("/auth/google/session")
async def google_auth_session(request: Request, response: Response):
    """Exchange Emergent session_id for user data and set session cookie"""
    body = await request.json()
    session_id = body.get('session_id')
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Call Emergent Auth to get user data
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        auth_data = auth_response.json()
    
    email = auth_data.get('email')
    name = auth_data.get('name', '')
    picture = auth_data.get('picture', '')
    session_token = auth_data.get('session_token')
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user['id']
        # Update user info if needed
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture}}
        )
    else:
        # Create new user
        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "email": email,
            "name": name,
            "phone": "",
            "picture": picture,
            "auth_provider": "google",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(new_user)
    
    # Store session
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "email": email,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    
    # Get full user data
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})

    # Auto-grant owner privileges for Purnabramha owner
    if email == "jayanti.kathale@purnabramha.com":
        await db.users.update_one({"id": user_id}, {"$set": {"is_admin": True}})
        for part in [1, 2, 3]:
            exists = await db.book_purchases.find_one({"user_id": user_id, "part_number": part, "status": "completed"}, {"_id": 0})
            if not exists:
                await db.book_purchases.insert_one({"user_id": user_id, "part_number": part, "session_id": f"owner-grant-{part}", "status": "completed", "purchased_at": datetime.now(timezone.utc).isoformat()})
        if user_doc:
            user_doc["is_admin"] = True

    return {"user": user_doc, "token": session_token}

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    session_token = request.cookies.get('session_token')
    
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(
        key="session_token",
        path="/",
        secure=True,
        samesite="none"
    )
    
    return {"message": "Logged out successfully"}

# Push Notification Endpoints (basic structure)
@api_router.post("/push/subscribe")
async def subscribe_push(request: Request, current_user: dict = Depends(get_current_user)):
    """Store push notification subscription"""
    body = await request.json()
    subscription = body.get('subscription')
    
    if not subscription:
        raise HTTPException(status_code=400, detail="Subscription data required")
    
    await db.push_subscriptions.update_one(
        {"user_id": current_user['user_id']},
        {"$set": {
            "user_id": current_user['user_id'],
            "subscription": subscription,
            "created_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    return {"message": "Subscribed to push notifications"}

@api_router.delete("/push/unsubscribe")
async def unsubscribe_push(current_user: dict = Depends(get_current_user)):
    """Remove push notification subscription"""
    await db.push_subscriptions.delete_one({"user_id": current_user['user_id']})
    return {"message": "Unsubscribed from push notifications"}

@api_router.get("/locations", response_model=List[Location])
async def get_locations():
    locations = await db.locations.find({"is_active": True}, {"_id": 0}).to_list(100)
    return [Location(**loc) for loc in locations]


@api_router.get("/centers")
async def get_centers():
    """Public endpoint: returns active locations grouped by region for Table Booking.
    Each center has the shape expected by the user-facing TableBooking page."""
    locations = await db.locations.find({"is_active": True}, {"_id": 0}).to_list(100)
    india, australia = [], []
    for loc in locations:
        country = (loc.get("country") or "").lower()
        center_id = loc.get("center_id") or loc.get("id")
        is_aus = "australia" in country
        currency = loc.get("currency") or ("AUD" if is_aus else "INR")
        currency_symbol = loc.get("currency_symbol") or ("$" if is_aus else "₹")
        center = {
            "id": center_id,
            "name": loc.get("name", ""),
            "displayName": loc.get("display_name") or loc.get("name", ""),
            "city": loc.get("city", ""),
            "state": loc.get("state", ""),
            "country": loc.get("country", ""),
            "whatsapp": loc.get("whatsapp", ""),
            "phone": loc.get("phone", ""),
            "address": loc.get("address", ""),
            "currency": currency,
            "currencySymbol": currency_symbol,
            "isActive": loc.get("is_active", True),
            "services": loc.get("services") or ["dine-in", "pickup", "tiffin", "catering", "unlimited-breakfast"],
        }
        (australia if is_aus else india).append(center)
    return {"india": india, "australia": australia}

@api_router.get("/menu", response_model=List[MenuItem])
async def get_menu(category: Optional[str] = None, location_id: Optional[str] = None):
    query = {"is_available": True}
    if category:
        query["category"] = category
    
    items = await db.menu_items.find(query, {"_id": 0}).to_list(1000)
    return [MenuItem(**item) for item in items]

# ADMIN ENDPOINTS

@api_router.get("/admin/menu", response_model=List[MenuItem])
async def get_all_menu_items(current_user: dict = Depends(get_current_user)):
    items = await db.menu_items.find({}, {"_id": 0}).to_list(1000)
    return [MenuItem(**item) for item in items]

@api_router.post("/admin/menu", response_model=MenuItem)
async def create_menu_item(item_data: dict, current_user: dict = Depends(get_current_user)):
    item = MenuItem(
        id=str(uuid.uuid4()),
        name=item_data['name'],
        description=item_data['description'],
        category=item_data['category'],
        price=float(item_data.get('price_inr', 0)),
        price_inr=float(item_data.get('price_inr', 0)),
        price_aud=float(item_data.get('price_aud', 0)) if item_data.get('price_aud') else None,
        image_url=item_data.get('image_url'),
        is_veg=item_data.get('is_veg', True),
        is_available=item_data.get('is_available', True),
        no_onion_garlic=item_data.get('no_onion_garlic', False),
        fasting_friendly=item_data.get('fasting_friendly', False)
    )
    
    doc = item.model_dump()
    await db.menu_items.insert_one(doc)
    return item

@api_router.put("/admin/menu/{item_id}", response_model=MenuItem)
async def update_menu_item(item_id: str, item_data: dict, current_user: dict = Depends(get_current_user)):
    update_data = {
        "name": item_data['name'],
        "description": item_data['description'],
        "category": item_data['category'],
        "price": float(item_data.get('price_inr', 0)),
        "price_inr": float(item_data.get('price_inr', 0)),
        "price_aud": float(item_data.get('price_aud', 0)) if item_data.get('price_aud') else None,
        "image_url": item_data.get('image_url'),
        "is_veg": item_data.get('is_veg', True),
        "is_available": item_data.get('is_available', True),
        "no_onion_garlic": item_data.get('no_onion_garlic', False),
        "fasting_friendly": item_data.get('fasting_friendly', False)
    }
    
    await db.menu_items.update_one({"id": item_id}, {"$set": update_data})
    
    updated_item = await db.menu_items.find_one({"id": item_id}, {"_id": 0})
    return MenuItem(**updated_item)

@api_router.delete("/admin/menu/{item_id}")
async def delete_menu_item(item_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.menu_items.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"message": "Menu item deleted successfully"}

# HERO IMAGES - Public endpoint
@api_router.get("/hero-image")
async def get_active_hero_image():
    """Get the active hero image for the homepage"""
    hero = await db.hero_images.find_one({"is_active": True}, {"_id": 0})
    if hero:
        return hero
    # Return default if no hero image set
    return {
        "id": "default",
        "title": "Authentic Maharashtrian Flavors",
        "description": "Experience the richness of traditional recipes at India's largest Maharashtrian restaurant chain",
        "image_url": "https://images.pexels.com/photos/30769679/pexels-photo-30769679.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
        "is_active": True
    }

# HERO IMAGES - Admin endpoints
@api_router.get("/admin/hero-images", response_model=List[HeroImage])
async def get_hero_images(current_user: dict = Depends(get_current_user)):
    images = await db.hero_images.find({}, {"_id": 0}).to_list(100)
    return [HeroImage(**img) for img in images]

@api_router.post("/admin/hero-images", response_model=HeroImage)
async def create_hero_image(image_data: dict, current_user: dict = Depends(get_current_user)):
    # Deactivate other images if this one is active
    if image_data.get("is_active", True):
        await db.hero_images.update_many({}, {"$set": {"is_active": False}})
    hero = HeroImage(**image_data)
    await db.hero_images.insert_one(hero.model_dump())
    return hero

@api_router.put("/admin/hero-images/{image_id}", response_model=HeroImage)
async def update_hero_image(image_id: str, image_data: dict, current_user: dict = Depends(get_current_user)):
    # Deactivate other images if this one is being set to active
    if image_data.get("is_active", False):
        await db.hero_images.update_many({"id": {"$ne": image_id}}, {"$set": {"is_active": False}})
    await db.hero_images.update_one({"id": image_id}, {"$set": image_data})
    updated = await db.hero_images.find_one({"id": image_id}, {"_id": 0})
    return HeroImage(**updated)

@api_router.delete("/admin/hero-images/{image_id}")
async def delete_hero_image(image_id: str, current_user: dict = Depends(get_current_user)):
    await db.hero_images.delete_one({"id": image_id})
    return {"message": "Hero image deleted"}

# LOCATIONS
@api_router.get("/admin/locations", response_model=List[Location])
async def get_all_locations(current_user: dict = Depends(get_current_user)):
    locations = await db.locations.find({}, {"_id": 0}).to_list(100)
    return [Location(**loc) for loc in locations]

@api_router.post("/admin/locations", response_model=Location)
async def create_location(location_data: dict, current_user: dict = Depends(get_current_user)):
    location = Location(**location_data)
    await db.locations.insert_one(location.model_dump())
    return location

@api_router.put("/admin/locations/{location_id}", response_model=Location)
async def update_location(location_id: str, location_data: dict, current_user: dict = Depends(get_current_user)):
    await db.locations.update_one({"id": location_id}, {"$set": location_data})
    updated = await db.locations.find_one({"id": location_id}, {"_id": 0})
    return Location(**updated)

@api_router.delete("/admin/locations/{location_id}")
async def delete_location(location_id: str, current_user: dict = Depends(get_current_user)):
    """Hard-delete a location and cascade delete its center time-slot config by center_id."""
    # Capture center_id BEFORE deleting so cascade works correctly
    loc = await db.locations.find_one({"id": location_id}, {"_id": 0})
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    center_id = loc.get("center_id")
    await db.locations.delete_one({"id": location_id})
    # Cascade: remove center-specific timeslots for this center (if a center_id was set)
    if center_id:
        await db.center_timeslots.delete_one({"center_id": center_id})
    logger.info(f"Location deleted by {current_user.get('email')}: id={location_id} center_id={center_id}")
    return {"message": "Location deleted", "id": location_id, "center_id": center_id}

# VIDEOS
@api_router.get("/videos", response_model=List[Video])
async def get_videos(category: Optional[str] = None):
    query = {"is_active": True}
    if category:
        query["category"] = category
    videos = await db.videos.find(query, {"_id": 0}).to_list(100)
    for video in videos:
        if isinstance(video.get('created_at'), str):
            video['created_at'] = datetime.fromisoformat(video['created_at'])
    return [Video(**v) for v in videos]

@api_router.post("/admin/videos", response_model=Video)
async def create_video(video_data: dict, current_user: dict = Depends(get_current_user)):
    video = Video(**video_data)
    doc = video.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.videos.insert_one(doc)
    return video

@api_router.delete("/admin/videos/{video_id}")
async def delete_video(video_id: str, current_user: dict = Depends(get_current_user)):
    await db.videos.delete_one({"id": video_id})
    return {"message": "Video deleted"}

@api_router.post("/orders/pickup", response_model=PickupOrder)
async def create_pickup_order(order_data: PickupOrderCreate, current_user: dict = Depends(get_current_user)):
    order = PickupOrder(
        user_id=current_user['user_id'],
        location_id=order_data.location_id,
        items=order_data.items,
        total_amount=sum(item.price * item.quantity for item in order_data.items),
        pickup_time=order_data.pickup_time,
        payment_method=order_data.payment_method
    )
    
    doc = order.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.pickup_orders.insert_one(doc)
    return order

@api_router.get("/orders/pickup", response_model=List[PickupOrder])
async def get_pickup_orders(current_user: dict = Depends(get_current_user)):
    orders = await db.pickup_orders.find({"user_id": current_user['user_id']}, {"_id": 0}).to_list(100)
    for order in orders:
        if isinstance(order.get('created_at'), str):
            order['created_at'] = datetime.fromisoformat(order['created_at'])
    return [PickupOrder(**order) for order in orders]

@api_router.post("/bookings/table", response_model=TableBooking)
async def create_table_booking(booking_data: TableBookingCreate, current_user: dict = Depends(get_current_user)):
    booking = TableBooking(
        user_id=current_user['user_id'],
        **booking_data.model_dump()
    )
    
    doc = booking.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.table_bookings.insert_one(doc)
    return booking

@api_router.get("/bookings/table", response_model=List[TableBooking])
async def get_table_bookings(current_user: dict = Depends(get_current_user)):
    bookings = await db.table_bookings.find({"user_id": current_user['user_id']}, {"_id": 0}).to_list(100)
    for booking in bookings:
        if isinstance(booking.get('created_at'), str):
            booking['created_at'] = datetime.fromisoformat(booking['created_at'])
    return [TableBooking(**booking) for booking in bookings]

@api_router.post("/tiffin/subscribe", response_model=TiffinSubscription)
async def create_tiffin_subscription(sub_data: TiffinSubscriptionCreate, current_user: dict = Depends(get_current_user)):
    subscription = TiffinSubscription(
        user_id=current_user['user_id'],
        **sub_data.model_dump()
    )
    
    doc = subscription.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.tiffin_subscriptions.insert_one(doc)
    return subscription

@api_router.get("/tiffin/subscriptions", response_model=List[TiffinSubscription])
async def get_tiffin_subscriptions(current_user: dict = Depends(get_current_user)):
    subs = await db.tiffin_subscriptions.find({"user_id": current_user['user_id']}, {"_id": 0}).to_list(100)
    for sub in subs:
        if isinstance(sub.get('created_at'), str):
            sub['created_at'] = datetime.fromisoformat(sub['created_at'])
    return [TiffinSubscription(**sub) for sub in subs]

@api_router.post("/catering/request", response_model=CateringRequest)
async def create_catering_request(req_data: CateringRequestCreate, current_user: dict = Depends(get_current_user)):
    request = CateringRequest(
        user_id=current_user['user_id'],
        **req_data.model_dump()
    )
    
    doc = request.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.catering_requests.insert_one(doc)
    return request

@api_router.get("/catering/requests", response_model=List[CateringRequest])
async def get_catering_requests(current_user: dict = Depends(get_current_user)):
    requests = await db.catering_requests.find({"user_id": current_user['user_id']}, {"_id": 0}).to_list(100)
    for req in requests:
        if isinstance(req.get('created_at'), str):
            req['created_at'] = datetime.fromisoformat(req['created_at'])
    return [CateringRequest(**req) for req in requests]

# ===================== TIFFIN CONFIG API =====================

class TiffinItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    price_inr: float
    price_aud: float
    category: str  # lunch_box, heavy_brunch, drink_addon
    is_available: bool = True
    image_url: Optional[str] = ""

class TiffinConfig(BaseModel):
    unlimited_breakfast_price_inr: float = 299
    unlimited_breakfast_price_aud: float = 35
    unlimited_breakfast_description: str = "Unlimited traditional Maharashtrian breakfast buffet"
    unlimited_breakfast_timings: str = "8:00 AM - 11:00 AM"
    unlimited_breakfast_days: List[str] = ["Saturday", "Sunday"]

@api_router.get("/tiffin-items")
async def get_tiffin_items():
    items = await db.tiffin_items.find({"is_available": True}, {"_id": 0}).to_list(500)
    return items

@api_router.get("/admin/tiffin-items")
async def get_admin_tiffin_items(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    items = await db.tiffin_items.find({}, {"_id": 0}).to_list(500)
    return items

@api_router.post("/admin/tiffin-items")
async def create_tiffin_item(item: TiffinItem, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    item_dict = item.model_dump()
    await db.tiffin_items.insert_one({**item_dict})  # Insert a copy to avoid _id mutation
    return {"message": "Tiffin item created", "item": item_dict}

@api_router.put("/admin/tiffin-items/{item_id}")
async def update_tiffin_item(item_id: str, item: TiffinItem, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    item_dict = item.model_dump()
    item_dict['id'] = item_id
    result = await db.tiffin_items.update_one({"id": item_id}, {"$set": item_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Tiffin item updated"}

@api_router.delete("/admin/tiffin-items/{item_id}")
async def delete_tiffin_item(item_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await db.tiffin_items.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Tiffin item deleted"}

@api_router.get("/tiffin-config")
async def get_tiffin_config():
    config = await db.tiffin_config.find_one({}, {"_id": 0})
    if not config:
        # Return default config
        return {
            "unlimited_breakfast_price_inr": 299,
            "unlimited_breakfast_price_aud": 35,
            "unlimited_breakfast_description": "Unlimited traditional Maharashtrian breakfast buffet",
            "unlimited_breakfast_timings": "8:00 AM - 11:00 AM",
            "unlimited_breakfast_days": ["Saturday", "Sunday"]
        }
    return config

@api_router.put("/admin/tiffin-config")
async def update_tiffin_config(config: TiffinConfig, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    config_dict = config.model_dump()
    await db.tiffin_config.update_one({}, {"$set": config_dict}, upsert=True)
    return {"message": "Tiffin config updated"}


# ===================== CATERING ADMIN API =====================

class CateringPackage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # Classic, Premium, Special Feast, Royal Feast
    description: str
    price_per_person_inr: float
    price_per_person_aud: float
    is_popular: bool = False
    requirements: dict  # {"starters": 1, "mains": 2, ...}
    is_active: bool = True
    display_order: int = 0

class CateringMenuItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = ""
    category: str  # starters, specialBhaji, simpleBhaji, desserts, roti, rice, drinks, sides, chutney
    image_url: Optional[str] = ""
    is_veg: bool = True
    is_available: bool = True

# Get catering packages (public)
@api_router.get("/catering-packages")
async def get_catering_packages():
    packages = await db.catering_packages.find({"is_active": True}, {"_id": 0}).to_list(100)
    if not packages:
        # Return data from JSON file as fallback
        json_path = Path(__file__).parent.parent / 'frontend' / 'src' / 'config' / 'catering-packages.json'
        if json_path.exists():
            with open(json_path) as f:
                data = json.load(f)
                return {"packages": data.get("packages", {}), "menuOptions": data.get("menuOptions", {})}
        return {"packages": {}, "menuOptions": {}}
    
    menu_items = await db.catering_menu_items.find({"is_available": True}, {"_id": 0}).to_list(500)
    
    # Organize packages by region
    india_packages = [p for p in packages if 'inr' in str(p.get('price_per_person_inr', 0)) or p.get('price_per_person_inr')]
    australia_packages = [p for p in packages if p.get('price_per_person_aud')]
    
    # Organize menu items by category
    menu_options = {}
    for item in menu_items:
        cat = item['category']
        if cat not in menu_options:
            menu_options[cat] = []
        menu_options[cat].append(item)
    
    return {
        "packages": {"india": packages, "australia": packages},
        "menuOptions": menu_options
    }

# Get all catering packages (admin)
@api_router.get("/admin/catering-packages")
async def get_admin_catering_packages(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    packages = await db.catering_packages.find({}, {"_id": 0}).to_list(100)
    return packages

# Create catering package
@api_router.post("/admin/catering-packages")
async def create_catering_package(package: CateringPackage, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    package_dict = package.model_dump()
    await db.catering_packages.insert_one({**package_dict})
    return {"message": "Package created", "package": package_dict}

# Update catering package
@api_router.put("/admin/catering-packages/{package_id}")
async def update_catering_package(package_id: str, package: CateringPackage, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    package_dict = package.model_dump()
    package_dict['id'] = package_id
    result = await db.catering_packages.update_one({"id": package_id}, {"$set": package_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Package not found")
    return {"message": "Package updated"}

# Delete catering package
@api_router.delete("/admin/catering-packages/{package_id}")
async def delete_catering_package(package_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await db.catering_packages.delete_one({"id": package_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Package not found")
    return {"message": "Package deleted"}

# Get all catering menu items (admin)
@api_router.get("/admin/catering-menu")
async def get_admin_catering_menu(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    items = await db.catering_menu_items.find({}, {"_id": 0}).to_list(500)
    return items

# Create catering menu item
@api_router.post("/admin/catering-menu")
async def create_catering_menu_item(item: CateringMenuItem, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    item_dict = item.model_dump()
    await db.catering_menu_items.insert_one({**item_dict})
    return {"message": "Item created", "item": item_dict}

# Update catering menu item
@api_router.put("/admin/catering-menu/{item_id}")
async def update_catering_menu_item(item_id: str, item: CateringMenuItem, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    item_dict = item.model_dump()
    item_dict['id'] = item_id
    result = await db.catering_menu_items.update_one({"id": item_id}, {"$set": item_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item updated"}

# Delete catering menu item
@api_router.delete("/admin/catering-menu/{item_id}")
async def delete_catering_menu_item(item_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = await db.catering_menu_items.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}

# Seed catering data from JSON
@api_router.post("/admin/catering-seed")
async def seed_catering_data(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    json_path = Path(__file__).parent.parent / 'frontend' / 'src' / 'config' / 'catering-packages.json'
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Catering config file not found")
    
    with open(json_path) as f:
        data = json.load(f)
    
    # Seed packages
    packages_seeded = 0
    for region, packages in data.get("packages", {}).items():
        for pkg in packages:
            existing = await db.catering_packages.find_one({"name": pkg['name'], "price_per_person_inr" if region == 'india' else "price_per_person_aud": pkg['pricePerPerson']})
            if not existing:
                catering_pkg = {
                    "id": str(uuid.uuid4()),
                    "name": pkg['name'],
                    "description": pkg.get('description', ''),
                    "price_per_person_inr": pkg['pricePerPerson'] if region == 'india' else 0,
                    "price_per_person_aud": pkg['pricePerPerson'] if region == 'australia' else 0,
                    "is_popular": pkg.get('isPopular', False),
                    "requirements": pkg.get('requirements', {}),
                    "is_active": True,
                    "display_order": int(pkg['id'].split('-')[1]) if '-' in pkg['id'] else 0
                }
                await db.catering_packages.insert_one(catering_pkg)
                packages_seeded += 1
    
    # Seed menu items
    items_seeded = 0
    for category, items in data.get("menuOptions", {}).items():
        for item in items:
            existing = await db.catering_menu_items.find_one({"name": item['name'], "category": category})
            if not existing:
                menu_item = {
                    "id": str(uuid.uuid4()),
                    "name": item['name'],
                    "description": "",
                    "category": category,
                    "image_url": "",
                    "is_veg": item.get('isVeg', True),
                    "is_available": True
                }
                await db.catering_menu_items.insert_one(menu_item)
                items_seeded += 1
    
    return {"message": f"Seeded {packages_seeded} packages and {items_seeded} menu items"}

# ===================== FESTIVAL THEME API =====================

class FestivalTheme(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    month: int  # 1-12
    name: str  # Festival name
    description: Optional[str] = ""
    primary_color: str = "#FF6B00"  # Orange (default)
    secondary_color: str = "#FFA500"
    accent_color: str = "#FFD700"
    banner_image_url: Optional[str] = ""
    greeting_text: str = ""
    is_active: bool = False
    start_date: Optional[str] = None  # e.g., "2025-03-21"
    end_date: Optional[str] = None

# Pre-defined Maharashtrian/Indian festivals
FESTIVAL_PRESETS = {
    1: {"name": "Makar Sankranti", "primary_color": "#FF6B00", "secondary_color": "#FFA500", "accent_color": "#FFEB3B", "greeting_text": "तिळगुळ घ्या गोड गोड बोला!"},
    2: {"name": "Maha Shivaratri", "primary_color": "#3F51B5", "secondary_color": "#7986CB", "accent_color": "#C5CAE9", "greeting_text": "हर हर महादेव!"},
    3: {"name": "Gudhi Padwa / Ugadi", "primary_color": "#FF9800", "secondary_color": "#FFB74D", "accent_color": "#FFF59D", "greeting_text": "गुढीपाडव्याच्या हार्दिक शुभेच्छा! नववर्षाच्या शुभेच्छा!"},
    4: {"name": "Hanuman Jayanti", "primary_color": "#F44336", "secondary_color": "#FF8A80", "accent_color": "#FFCDD2", "greeting_text": "जय श्री राम! जय हनुमान!"},
    5: {"name": "Buddha Purnima", "primary_color": "#9C27B0", "secondary_color": "#CE93D8", "accent_color": "#E1BEE7", "greeting_text": "बुद्धं शरणं गच्छामि"},
    6: {"name": "Vat Purnima", "primary_color": "#4CAF50", "secondary_color": "#81C784", "accent_color": "#C8E6C9", "greeting_text": "वटपौर्णिमेच्या शुभेच्छा!"},
    7: {"name": "Guru Purnima", "primary_color": "#FF5722", "secondary_color": "#FF8A65", "accent_color": "#FFCCBC", "greeting_text": "गुरुर्ब्रह्मा गुरुर्विष्णु"},
    8: {"name": "Janmashtami / Gokulashtami", "primary_color": "#2196F3", "secondary_color": "#64B5F6", "accent_color": "#BBDEFB", "greeting_text": "गोविंदा आला रे!"},
    9: {"name": "Ganesh Chaturthi", "primary_color": "#FF6B00", "secondary_color": "#FF9800", "accent_color": "#FFE082", "greeting_text": "गणपती बाप्पा मोरया!"},
    10: {"name": "Navratri / Dasara", "primary_color": "#E91E63", "secondary_color": "#F48FB1", "accent_color": "#F8BBD9", "greeting_text": "नवरात्रीच्या शुभेच्छा!"},
    11: {"name": "Diwali", "primary_color": "#FFC107", "secondary_color": "#FFEB3B", "accent_color": "#FFF9C4", "greeting_text": "दीपावलीच्या हार्दिक शुभेच्छा! 🪔"},
    12: {"name": "Christmas / New Year", "primary_color": "#D32F2F", "secondary_color": "#4CAF50", "accent_color": "#FFEB3B", "greeting_text": "Merry Christmas & Happy New Year!"}
}

@api_router.get("/festival-theme")
async def get_active_festival_theme():
    """Get the currently active festival theme for the website"""
    # Check for active theme
    theme = await db.festival_themes.find_one({"is_active": True}, {"_id": 0})
    if theme:
        return theme
    
    # Check if any theme matches current month
    from datetime import datetime
    current_month = datetime.now().month
    month_theme = await db.festival_themes.find_one({"month": current_month}, {"_id": 0})
    if month_theme:
        return month_theme
    
    # Return default (no festival)
    return {
        "id": "default",
        "month": 0,
        "name": "",
        "is_active": False,
        "primary_color": "#FF6B00",
        "secondary_color": "#FFA500",
        "accent_color": "#FFD700"
    }

@api_router.get("/admin/festival-themes")
async def get_all_festival_themes(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all festival themes for admin management"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    themes = await db.festival_themes.find({}, {"_id": 0}).to_list(20)
    
    # If no themes exist, initialize with presets
    if not themes:
        themes = []
        for month, preset in FESTIVAL_PRESETS.items():
            theme = {
                "id": str(uuid.uuid4()),
                "month": month,
                "name": preset["name"],
                "description": "",
                "primary_color": preset["primary_color"],
                "secondary_color": preset["secondary_color"],
                "accent_color": preset["accent_color"],
                "greeting_text": preset["greeting_text"],
                "banner_image_url": "",
                "is_active": False
            }
            await db.festival_themes.insert_one({**theme})  # Insert a copy to avoid _id mutation
            themes.append(theme)
    
    return sorted(themes, key=lambda x: x.get("month", 0))

@api_router.put("/admin/festival-themes/{theme_id}")
async def update_festival_theme(theme_id: str, theme_data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Update a festival theme"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # If setting as active, deactivate others
    if theme_data.get("is_active"):
        await db.festival_themes.update_many({}, {"$set": {"is_active": False}})
    
    await db.festival_themes.update_one({"id": theme_id}, {"$set": theme_data})
    updated = await db.festival_themes.find_one({"id": theme_id}, {"_id": 0})
    return updated

@api_router.post("/admin/festival-themes")
async def create_festival_theme(theme_data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Create a new festival theme"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    theme_data["id"] = str(uuid.uuid4())
    if theme_data.get("is_active"):
        await db.festival_themes.update_many({}, {"$set": {"is_active": False}})
    
    await db.festival_themes.insert_one({**theme_data})  # Insert a copy
    return theme_data

@api_router.delete("/admin/festival-themes/{theme_id}")
async def delete_festival_theme(theme_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Delete a festival theme"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await db.festival_themes.delete_one({"id": theme_id})
    return {"message": "Festival theme deleted"}

# ===================== SCAN DISH (IMAGE RECOGNITION) API =====================

@api_router.post("/scan-dish")
async def scan_dish(request: Request):
    """Identify a dish from a photo and return its menu match + nutrition."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    body = await request.json()
    image_base64 = body.get("image_base64")
    if not image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    # Get all menu item names for matching
    all_items = await db.menu_items.find({"is_available": True}, {"_id": 0}).to_list(1000)
    item_names = [item["name"] for item in all_items]

    prompt = f"""You are a food recognition expert specializing in Indian/Maharashtrian cuisine from the restaurant "Purnabramha".

Look at this food photo and identify which dish it is from our menu. Here are all the dishes on our menu:

{json.dumps(item_names)}

Return ONLY a valid JSON object (no markdown, no code blocks) with this exact structure:
{{"identified_dish": "<exact name from the menu list above>", "confidence": "<high/medium/low>", "description": "<brief 1-line description of what you see in the image>"}}

Rules:
- Match to the CLOSEST dish from the menu list above
- If you cannot identify the dish at all, return: {{"identified_dish": "unknown", "confidence": "low", "description": "<what you see>"}}
- Use the EXACT dish name from the menu list
- Be generous in matching - if it looks like any Indian dish on the menu, match it"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"scan-{uuid.uuid4()}",
            system_message="You are a food recognition expert. Return only valid JSON."
        ).with_model("openai", "gpt-4.1")

        image_content = ImageContent(image_base64=image_base64)
        user_message = UserMessage(text=prompt, file_contents=[image_content])
        response = await chat.send_message(user_message)

        # Parse response
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        result = json.loads(response_text)
        identified_name = result.get("identified_dish", "unknown")

        # Find matching menu item
        matched_item = None
        for item in all_items:
            if item["name"].lower() == identified_name.lower():
                matched_item = item
                break

        # Fuzzy match if exact match fails
        if not matched_item and identified_name != "unknown":
            for item in all_items:
                if identified_name.lower() in item["name"].lower() or item["name"].lower() in identified_name.lower():
                    matched_item = item
                    break

        if not matched_item:
            return {
                "success": False,
                "message": "Could not identify this dish from our menu. Try a clearer photo!",
                "ai_description": result.get("description", ""),
                "confidence": result.get("confidence", "low")
            }

        # Get nutrition data
        nutrition = await db.nutrition_info.find_one({"menu_item_id": matched_item["id"]}, {"_id": 0})
        if not nutrition:
            try:
                nutrition = await generate_nutrition_for_item(matched_item)
            except Exception:
                nutrition = None

        return {
            "success": True,
            "matched_item": {
                "id": matched_item["id"],
                "name": matched_item["name"],
                "description": matched_item.get("description", ""),
                "category": matched_item.get("category", ""),
                "price_inr": matched_item.get("price_inr"),
                "price_aud": matched_item.get("price_aud"),
                "image_url": matched_item.get("image_url"),
                "is_veg": matched_item.get("is_veg", True),
                "no_onion_garlic": matched_item.get("no_onion_garlic", False),
                "fasting_friendly": matched_item.get("fasting_friendly", False)
            },
            "nutrition": nutrition,
            "confidence": result.get("confidence", "medium"),
            "ai_description": result.get("description", "")
        }

    except json.JSONDecodeError:
        logger.error(f"Failed to parse scan result: {response_text[:200]}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        logger.error(f"Scan dish error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to scan dish: {str(e)}")


# ===================== NUTRITION INFO API =====================

@api_router.get("/nutrition/{item_id}")
async def get_nutrition_info(item_id: str):
    """Get nutrition info for a menu item. Generates via AI if not cached."""
    # Check cache first
    cached = await db.nutrition_info.find_one({"menu_item_id": item_id}, {"_id": 0})
    if cached:
        return cached

    # Get menu item details
    item = await db.menu_items.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Generate via AI
    nutrition = await generate_nutrition_for_item(item)
    return nutrition


async def generate_nutrition_for_item(item: dict) -> dict:
    """Use GPT to generate nutrition info for a dish."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    prompt = f"""You are a professional Indian food nutritionist. Analyze this Maharashtrian vegetarian dish and return ONLY a valid JSON object (no markdown, no code blocks).

Dish: {item['name']}
Description: {item.get('description', '')}
Category: {item.get('category', '')}
Is Vegetarian: {item.get('is_veg', True)}
No Onion/Garlic (Jain): {item.get('no_onion_garlic', False)}
Fasting Friendly (Upvas): {item.get('fasting_friendly', False)}

Return this exact JSON structure:
{{"calories": <number kcal per serving>, "protein": <number grams>, "carbs": <number grams>, "fats": <number grams>, "fiber": <number grams>, "serving_size": "<e.g. 1 plate / 1 piece / 1 bowl>", "health_benefits": ["<benefit 1>", "<benefit 2>", "<benefit 3>", "<benefit 4>"], "allergens": ["<allergen1>", "<allergen2>"], "ayurvedic_benefits": "<1-2 sentence traditional Ayurvedic/Maharashtrian health wisdom about this dish>", "dietary_tags": ["<tag1>", "<tag2>"]}}

Guidelines:
- Estimate realistic nutrition for a standard restaurant serving
- Health benefits should be specific to THIS dish's ingredients
- Include allergens like Dairy, Nuts, Gluten, Soy only if applicable
- Dietary tags examples: High Protein, Low Calorie, Rich in Iron, Fiber Rich, Calcium Rich, Antioxidant Rich
- Ayurvedic benefits should reference traditional Maharashtrian/Indian food wisdom
- For thalis, estimate the full plate
- Return ONLY the JSON, nothing else"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"nutrition-{item['id']}",
            system_message="You are a food nutrition expert. Return only valid JSON."
        ).with_model("openai", "gpt-4.1-mini")

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)

        # Parse the response - handle potential markdown wrapping
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        nutrition_data = json.loads(response_text)

        # Build the document
        doc = {
            "menu_item_id": item["id"],
            "menu_item_name": item["name"],
            "calories": int(nutrition_data.get("calories", 0)),
            "protein": round(float(nutrition_data.get("protein", 0)), 1),
            "carbs": round(float(nutrition_data.get("carbs", 0)), 1),
            "fats": round(float(nutrition_data.get("fats", 0)), 1),
            "fiber": round(float(nutrition_data.get("fiber", 0)), 1),
            "serving_size": nutrition_data.get("serving_size", "1 serving"),
            "health_benefits": nutrition_data.get("health_benefits", []),
            "allergens": nutrition_data.get("allergens", []),
            "ayurvedic_benefits": nutrition_data.get("ayurvedic_benefits", ""),
            "dietary_tags": nutrition_data.get("dietary_tags", []),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        # Cache in DB
        await db.nutrition_info.update_one(
            {"menu_item_id": item["id"]},
            {"$set": doc},
            upsert=True
        )

        return doc

    except json.JSONDecodeError:
        logger.error(f"Failed to parse nutrition JSON for {item['name']}: {response_text[:200]}")
        raise HTTPException(status_code=500, detail="Failed to parse nutrition data")
    except Exception as e:
        logger.error(f"Failed to generate nutrition for {item['name']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate nutrition: {str(e)}")


@api_router.post("/admin/nutrition/generate/{item_id}")
async def admin_generate_nutrition(item_id: str, current_user: dict = Depends(get_current_user)):
    """Admin: Force regenerate nutrition for a specific item."""
    item = await db.menu_items.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Delete existing cache to force regeneration
    await db.nutrition_info.delete_one({"menu_item_id": item_id})
    nutrition = await generate_nutrition_for_item(item)
    return nutrition


@api_router.post("/admin/nutrition/generate-bulk")
async def admin_generate_nutrition_bulk(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Generate nutrition for all items that don't have it yet. Returns count immediately, processes in background."""
    body = await request.json()
    force = body.get("force", False)

    items = await db.menu_items.find({"is_available": True}, {"_id": 0}).to_list(1000)

    # Count how many need generation
    need_generation = 0
    already_have = 0
    for item in items:
        existing = await db.nutrition_info.find_one({"menu_item_id": item["id"]})
        if existing and not force:
            already_have += 1
        else:
            need_generation += 1

    # Generate for first 10 items immediately (rest will be generated on-demand when clicked)
    generated = 0
    errors = 0
    for item in items[:10]:
        if not force:
            existing = await db.nutrition_info.find_one({"menu_item_id": item["id"]})
            if existing:
                continue

        try:
            await generate_nutrition_for_item(item)
            generated += 1
        except Exception as e:
            logger.error(f"Bulk nutrition error for {item['name']}: {str(e)}")
            errors += 1

    return {
        "message": "Bulk generation complete",
        "generated": generated,
        "skipped": already_have,
        "errors": errors,
        "total": len(items),
        "note": f"Generated {generated} now. Remaining items will auto-generate when customers view them."
    }


@api_router.put("/admin/nutrition/{item_id}")
async def admin_update_nutrition(item_id: str, nutrition_data: dict, current_user: dict = Depends(get_current_user)):
    """Admin: Manually edit nutrition info for an item."""
    nutrition_data["menu_item_id"] = item_id
    nutrition_data["generated_at"] = datetime.now(timezone.utc).isoformat()

    await db.nutrition_info.update_one(
        {"menu_item_id": item_id},
        {"$set": nutrition_data},
        upsert=True
    )

    updated = await db.nutrition_info.find_one({"menu_item_id": item_id}, {"_id": 0})
    return updated


# ===================== ASK VAHINI - AI FOOD WISDOM ENGINE =====================

VAHINI_SYSTEM_PROMPT = """You are "Vahini" — the AI Food Wisdom persona of Purnabramha restaurant, modeled after the warmth and wisdom of Mrs. Jayanti Kathale, the founder.

PERSONALITY:
- You are a caring Maharashtrian Vahini (sister-in-law) who deeply understands food, health, seasons, and tradition
- Your tone is warm, respectful, calm, and culturally rooted
- You give simple, practical food advice rooted in Maharashtrian kitchen wisdom
- You ALWAYS begin your FIRST greeting with "Jai Hind Namaskar." (only for the first message in a conversation)
- You speak with affection, like a family elder guiding someone about food

RULES:
- NEVER share or hint at recipes. Purnabramha recipes are a closely guarded secret. If someone asks for a recipe, lovingly redirect them: "Vahini keeps her recipes secret! But you can enjoy this dish at any Purnabramha center."
- Always recommend dishes that are ACTUALLY on the Purnabramha menu (provided below)
- IMPORTANT: Items starting with "BG" or from "Balgopal" category are KIDS MENU items (BG = Balgopal = kids). NEVER recommend BG/Balgopal items to adults. Only suggest them when the user specifically asks about food for kids or children.
- Consider the user's context: health concern, mood, weather, time of day, festival season
- Give brief cultural or health significance with each recommendation
- Keep responses concise and warm (2-4 short paragraphs maximum)
- Do not use markdown formatting like ** or ## in your responses. Use plain text.
- IMPORTANT: Purnabramha has launched the BANANA LEAF THALI - an unlimited authentic Maharashtrian thali served on a traditional banana leaf. Available every Tuesday, Wednesday, and Thursday, LUNCH ONLY. Price: Rs.490 per person in India, $40 in Perth. Non-sharable. Available at ALL centers. Hinjewadi and Kharadi have 200+ FREE parking. Recommend this enthusiastically when users ask about thali, lunch options, group dining, or corporate meals on Tue/Wed/Thu. Also mention it's perfect for corporates.

SERVICES YOU HELP WITH (when a guest asks where/how to do something, walk them through the flow step-by-step in 3-5 short bullet-like sentences, then provide an "action" button so they can jump straight to that page):

1. CELEBRATE / EVENT BOOKING (weddings, anniversaries, birthdays, haldi, munj, naming ceremony, family gatherings):
   - Page path: /wedding-booking
   - Flow: (a) Fill your name, mobile, email (b) Pick event type + center + date + guest count + time slot (c) Choose a Thali Package: Royal Feast (signature multi-course) or Premium Feast (curated classic) (d) Inside Menu Selection card, pick your Dal/Varan/Amti choices, Starters, Mains, Sweets, Roti, Rice, Sides, Chutney based on the package's allowance (Royal allows more picks than Premium) (e) Optionally add Breakfast, Evening Snacks, Drinks service, Decoration (f) Live Estimate updates with GST (g) Tap "Send Enquiry via WhatsApp" — our team contacts you within hours with the final quotation. You also get a shareable quotation link to forward to family.
   - Min guests: usually 30. Hall + per-person thali pricing. Both India (₹) and Perth ($) supported.

2. TIFFIN / DAILY SUBSCRIPTION:
   - Page path: /tiffin
   - Flow: (a) Pick your region (India / Australia) + center (b) Choose a combo — Roti Combo, Bhakari Combo, Special Thali Box, or our Heavy Brunch (c) Pick subscription frequency (1 day, weekly, monthly) (d) Enter delivery address + contact (e) Confirm via WhatsApp. Heavy Brunch has special savings vs dine-in pricing.
   - Best for: working professionals, students, families wanting home-style daily meals without cooking.

3. TABLE BOOKING (Dine-in):
   - Page path: /table-booking
   - Flow: (a) Choose center + date + time slot + number of guests (b) Pick from special dining experiences: Banana Leaf Thali (Tue/Wed/Thu lunch only, ₹490 India / $40 Perth, unlimited), Unlimited Breakfast (Saturdays and Sundays ONLY), regular a-la-carte. (c) Live promos sometimes available — Brunch 10% off (11 AM – 12 PM) and Evening Snack 10% off (4 PM – 5 PM) on selected days (d) Submit and arrive at your reserved time.
   - Tip: Unlimited Breakfast is weekend-exclusive — perfect for family Sunday brunches.

4. PICKUP ORDER (Takeaway):
   - Page path: /pickup
   - Flow: (a) Choose nearest center (b) Browse the live menu by category (c) Tap dishes to add to cart — cart appears as a bottom sheet on mobile, side panel on desktop (d) Apply combo promos if active (Brunch 10% off between 11-12, Evening Snack 10% off between 4-5) (e) Enter pickup time + your name + mobile (f) Confirm via WhatsApp and pick up at the chosen time.
   - Tip: Time your order to catch the live brunch or evening-snack discount window.

5. OTHER USEFUL PAGES:
   - /catering — large bulk catering (separate from Celebrate) with package + crockery + staff add-ons
   - /locations — find your nearest Purnabramha center, contact numbers, parking
   - /book — read our book "When a Restaurant Becomes Human"
   - /menu — browse the full a-la-carte menu
   - /guest-card — share honest feedback after a visit and instantly receive a Purnabramha discount card with a unique coupon code to use on the next visit. Always nudge guests towards this page after they tell you about a good (or bad) experience.

WHEN A GUEST ASKS "WHERE / HOW DO I…":
- Detect their intent and identify which of the 5 services they need.
- Reply with a short, friendly summary of the flow (3-5 sentences).
- ALWAYS include 1-2 entries in the "actions" array pointing them to the correct page. The "label" should be inviting ("Plan my celebration", "Subscribe to tiffin", "Book a table", "Open pickup menu") and "path" must be the exact route above.
- If the user is just chit-chatting about food, leave "actions" empty.

RESPONSE FORMAT:
You MUST respond with ONLY a valid JSON object (no markdown, no code blocks). Use this exact structure:
{"message": "<your warm response text here>", "recommended_dishes": ["<Exact Dish Name from Menu 1>"], "cultural_note": "<brief cultural/health wisdom>", "actions": [{"label": "<button text>", "path": "</page-path>"}]}

- "message" should be your full conversational response
- "recommended_dishes" should contain 0-3 EXACT dish names from the menu list provided (can be empty for service-flow questions)
- "cultural_note" is a short one-liner of traditional wisdom (optional, can be empty)
- "actions" is 0-2 CTA buttons pointing to relevant service pages (empty array if pure food chat)
- If the user is just chatting or greeting, recommended_dishes and actions can both be empty
- Use the EXACT dish names from the menu, not abbreviated forms"""

class VahiniChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[dict] = None  # {mood, health, weather, time_of_day}

@api_router.post("/vahini/chat")
async def vahini_chat(req: VahiniChatRequest):
    """Chat with Vahini - the AI Food Wisdom Engine."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import random

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")

    # Get menu items for grounding — exclude BG/Balgopal (kids) items for adult recommendations
    all_items = await db.menu_items.find({"is_available": True}, {"_id": 0}).to_list(1000)
    adult_items = [item for item in all_items if not item["name"].startswith("BG ") and item.get("category", "").lower() not in ["balgopal (kids menu)", "balgopal"]]
    kids_items = [item for item in all_items if item["name"].startswith("BG ") or item.get("category", "").lower() in ["balgopal (kids menu)", "balgopal"]]
    # Use adult items by default; include kids items only if user asks about kids/children
    user_asks_kids = any(w in req.message.lower() for w in ["kid", "child", "balgopal", "children", "baby", "toddler"])
    recommend_items = all_items if user_asks_kids else adult_items
    menu_names = [item["name"] for item in recommend_items]
    categories = list(set(item.get("category", "") for item in recommend_items))

    # Get active festival theme if any
    festival = await db.festival_themes.find_one({"is_active": True}, {"_id": 0})
    festival_context = ""
    if festival:
        festival_context = f"\nCurrent active festival: {festival.get('name', '')}. Suggest festival-appropriate dishes if relevant."

    # Pull live service config so Vahini quotes accurate, current prices
    wedding_cfg_doc = await db.wedding_config.find_one({"_id_key": "global"}, {"_id": 0}) or {}
    promo_cfg = await db.promotion_settings.find_one({"_id_key": "global"}, {"_id": 0}) or {}
    merged_wedding = {**DEFAULT_WEDDING_CONFIG, **wedding_cfg_doc}
    thali_pkgs_summary = []
    for p in (merged_wedding.get("thali_packages") or []):
        if p.get("enabled") is False:
            continue
        reqs = p.get("requirements") or {}
        thali_pkgs_summary.append(
            f"{p.get('name')}: ₹{p.get('price_inr')}/pp India · ${p.get('price_aud')}/pp Perth · "
            f"picks → dal {reqs.get('dal',0)}, starters {reqs.get('starters',0)}, special {reqs.get('special',0)}, "
            f"mains {reqs.get('mains',0)}, sweets {reqs.get('desserts',0)}, roti {reqs.get('roti',0)}, "
            f"rice {reqs.get('rice',0)}, sides {reqs.get('sides',0)}, chutney {reqs.get('chutney',0)}"
        )
    dal_names = [d.get("name") for d in (merged_wedding.get("dal_options") or []) if d.get("enabled") is not False]

    service_context = f"""
LIVE SERVICE PRICING (use these in your replies, never guess):
- Celebrate hall charge: ₹{merged_wedding.get('hall_charges_inr')} India / ${merged_wedding.get('hall_charges_aud')} Perth · min {merged_wedding.get('min_guests')} guests · GST {merged_wedding.get('gst_pct')}%
- Celebrate thali packages (Celebration-only, NOT same as Catering): {' | '.join(thali_pkgs_summary) if thali_pkgs_summary else 'currently unavailable'}
- Dal / Varan / Amti options for Celebrate: {', '.join(dal_names) if dal_names else 'currently unavailable'}
- Active promos: Brunch {promo_cfg.get('brunch', {}).get('inr_pct', 10)}% off 11AM–12PM · Evening Snack {promo_cfg.get('evening_snack', {}).get('inr_pct', 10)}% off 4PM–5PM (when enabled)
"""

    # Build context
    context_info = ""
    user_region = "India"
    if req.context:
        if req.context.get("mood"):
            context_info += f"\nUser's mood: {req.context['mood']}"
        if req.context.get("health"):
            context_info += f"\nUser's health concern: {req.context['health']}"
        if req.context.get("weather"):
            context_info += f"\nCurrent weather: {req.context['weather']}"
        if req.context.get("time_of_day"):
            context_info += f"\nTime of day: {req.context['time_of_day']}"
        if req.context.get("region"):
            user_region = req.context["region"]
            context_info += f"\nUser's region: {user_region}. Show prices in {'AUD ($)' if user_region == 'Australia' else 'INR (₹)'}. Mention the nearest Purnabramha center in {'Perth' if user_region == 'Australia' else 'India'}."

    # Check conversation history for context
    session_id = req.session_id or f"vahini-{uuid.uuid4()}"
    history = await db.vahini_chats.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(6).to_list(6)
    history.reverse()

    is_first_message = len(history) == 0

    menu_context = f"""
PURNABRAMHA MENU (recommend ONLY from these):
Categories: {', '.join(categories)}
Dishes: {', '.join(menu_names[:100])}
{festival_context}
{service_context}
{context_info}
{"This is the user's FIRST message - start with 'Jai Hind Namaskar.'" if is_first_message else "This is a follow-up message in the conversation - do NOT repeat 'Jai Hind Namaskar' greeting."}
"""

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=VAHINI_SYSTEM_PROMPT + menu_context
        ).with_model("openai", "gpt-4.1-mini")

        # Add conversation history for context
        for h in history[-4:]:
            if h.get("role") == "user":
                await chat.send_message(UserMessage(text=h["content"]))
            # assistant messages are auto-tracked by session

        user_message = UserMessage(text=req.message)
        response = await chat.send_message(user_message)

        # Parse AI response
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        try:
            ai_data = json.loads(response_text)
        except json.JSONDecodeError:
            ai_data = {"message": response_text, "recommended_dishes": [], "cultural_note": ""}

        # Match recommended dishes to actual menu items (use recommend_items to enforce BG filter)
        matched_dishes = []
        for dish_name in ai_data.get("recommended_dishes", []):
            for item in recommend_items:
                if item["name"].lower() == dish_name.lower():
                    matched_dishes.append({
                        "id": item["id"],
                        "name": item["name"],
                        "category": item.get("category", ""),
                        "price_inr": item.get("price_inr"),
                        "price_aud": item.get("price_aud"),
                        "image_url": item.get("image_url"),
                        "description": item.get("description", ""),
                        "no_onion_garlic": item.get("no_onion_garlic", False),
                        "fasting_friendly": item.get("fasting_friendly", False)
                    })
                    break
            else:
                # Fuzzy match — still only from recommend_items
                for item in recommend_items:
                    if dish_name.lower() in item["name"].lower() or item["name"].lower() in dish_name.lower():
                        matched_dishes.append({
                            "id": item["id"],
                            "name": item["name"],
                            "category": item.get("category", ""),
                            "price_inr": item.get("price_inr"),
                            "price_aud": item.get("price_aud"),
                            "image_url": item.get("image_url"),
                            "description": item.get("description", ""),
                            "no_onion_garlic": item.get("no_onion_garlic", False),
                            "fasting_friendly": item.get("fasting_friendly", False)
                        })
                        break

        # Strip any BG references from the AI message text for adult queries
        ai_message = ai_data.get("message", response_text)
        if not user_asks_kids:
            import re
            ai_message = re.sub(r'\bBG\s+', '', ai_message)
            ai_message = re.sub(r'\bBalgopal\b', '', ai_message)

        # Save conversation
        await db.vahini_chats.insert_one({
            "session_id": session_id,
            "role": "user",
            "content": req.message,
            "created_at": datetime.now(timezone.utc)
        })
        await db.vahini_chats.insert_one({
            "session_id": session_id,
            "role": "assistant",
            "content": ai_message,
            "recommended_dishes": [d["name"] for d in matched_dishes],
            "created_at": datetime.now(timezone.utc)
        })

        # Sanitize actions — only allow known service paths so the bot can't redirect anywhere unexpected
        ALLOWED_PATHS = {"/wedding-booking", "/tiffin", "/table-booking", "/pickup", "/catering", "/locations", "/book", "/menu", "/guest-card"}
        clean_actions = []
        for a in (ai_data.get("actions") or [])[:2]:
            try:
                lbl = str(a.get("label", "")).strip()[:60]
                pth = str(a.get("path", "")).strip()
                if lbl and pth in ALLOWED_PATHS:
                    clean_actions.append({"label": lbl, "path": pth})
            except Exception:
                continue

        return {
            "session_id": session_id,
            "message": ai_message,
            "recommended_dishes": matched_dishes,
            "cultural_note": ai_data.get("cultural_note", ""),
            "actions": clean_actions,
            "is_first_message": is_first_message
        }

    except Exception as e:
        logger.error(f"Vahini chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Vahini is resting right now. Please try again shortly.")


@api_router.get("/vahini/random-dish")
async def vahini_random_dish(region: Optional[str] = "India"):
    """Let Vahini choose a random dish for you."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import random

    all_items = await db.menu_items.find({"is_available": True}, {"_id": 0}).to_list(1000)
    if not all_items:
        raise HTTPException(status_code=404, detail="No menu items available")

    # Pick a random dish (exclude kids/BG items and drinks/tea)
    main_items = [i for i in all_items if
        i.get("category", "").lower() not in ["tea / coffee", "non tea / drinks", "tea-coffee", "drinks", "balgopal (kids menu)", "balgopal"]
        and not i["name"].startswith("BG ")
    ]
    # For Australia, only show items that have AUD pricing
    if region == "Australia":
        main_items = [i for i in main_items if i.get("price_aud")]
    if not main_items:
        main_items = all_items

    chosen = random.choice(main_items)

    # Get nutrition if available
    nutrition = await db.nutrition_info.find_one({"menu_item_id": chosen["id"]}, {"_id": 0})

    # Generate a short Vahini-style message
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    vahini_message = f"Today Vahini suggests you eat {chosen['name']}. It is a wonderful Maharashtrian dish that nourishes both body and soul."

    if api_key:
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=f"vahini-random-{uuid.uuid4()}",
                system_message="You are Vahini, a warm Maharashtrian food elder. In 2-3 sentences, lovingly recommend this dish. Mention one health or cultural benefit. Do not use markdown. Keep it warm and brief. Start with 'Today Vahini suggests you eat...'"
            ).with_model("openai", "gpt-4.1-mini")

            msg = UserMessage(text=f"Dish: {chosen['name']}, Category: {chosen.get('category', '')}, Description: {chosen.get('description', '')}")
            response = await chat.send_message(msg)
            vahini_message = response.strip()
        except Exception as e:
            logger.error(f"Vahini random message error: {str(e)}")

    return {
        "message": vahini_message,
        "dish": {
            "id": chosen["id"],
            "name": chosen["name"],
            "category": chosen.get("category", ""),
            "price_inr": chosen.get("price_inr"),
            "price_aud": chosen.get("price_aud"),
            "image_url": chosen.get("image_url"),
            "description": chosen.get("description", ""),
            "no_onion_garlic": chosen.get("no_onion_garlic", False),
            "fasting_friendly": chosen.get("fasting_friendly", False)
        },
        "nutrition": nutrition
    }


# ===================== BOOK READING PLATFORM =====================

BOOK_PARTS = {
    1: {"name": "Part 1", "pages": "1-50", "price_inr": 50.00, "price_aud": 1.00, "start_page": 1, "end_page": 50},
    2: {"name": "Part 2", "pages": "51-100", "price_inr": 50.00, "price_aud": 1.00, "start_page": 51, "end_page": 100},
    3: {"name": "Part 3", "pages": "101-152", "price_inr": 50.00, "price_aud": 1.00, "start_page": 101, "end_page": 152},
}

BOOK_BUNDLE = {
    "name": "Complete Book",
    "price_inr": 50.00,   # Discounted from ₹150
    "price_aud": 1.50,    # Discounted from $3
    "original_inr": 150.00,
    "original_aud": 3.00,
    "parts": [1, 2, 3]
}

@api_router.get("/book/parts")
async def get_book_parts(current_user: dict = Depends(get_optional_user)):
    """Get all book parts with purchase status for current user."""
    parts = []
    all_purchased = True
    for part_num, info in BOOK_PARTS.items():
        purchased = False
        if current_user:
            purchase = await db.book_purchases.find_one(
                {"user_id": current_user["user_id"], "part_number": part_num, "status": "completed"},
                {"_id": 0}
            )
            purchased = purchase is not None
        if not purchased:
            all_purchased = False
        parts.append({
            "part_number": part_num,
            "name": info["name"],
            "pages": info["pages"],
            "price_inr": info["price_inr"],
            "price_aud": info["price_aud"],
            "start_page": info["start_page"],
            "end_page": info["end_page"],
            "purchased": purchased
        })

    # Count how many unpurchased
    unpurchased = [p for p in parts if not p["purchased"]]

    return {
        "parts": parts,
        "bundle": {
            "price_inr": BOOK_BUNDLE["price_inr"],
            "price_aud": BOOK_BUNDLE["price_aud"],
            "original_inr": BOOK_BUNDLE["original_inr"],
            "original_aud": BOOK_BUNDLE["original_aud"],
            "all_purchased": all_purchased,
            "unpurchased_count": len(unpurchased)
        }
    }


FREE_PREVIEW_PAGES = 5  # First 5 pages free without login

@api_router.get("/book/pages/{part_number}")
async def get_book_pages(part_number: int, current_user: dict = Depends(get_optional_user)):
    """Get pages for a book part. First 5 pages are free preview."""
    if part_number not in BOOK_PARTS:
        raise HTTPException(status_code=404, detail="Invalid part number")

    part_info = BOOK_PARTS[part_number]
    is_purchased = False

    if current_user:
        purchase = await db.book_purchases.find_one(
            {"user_id": current_user["user_id"], "part_number": part_number, "status": "completed"},
            {"_id": 0}
        )
        is_purchased = purchase is not None

    # For Part 1: allow free preview of first N pages
    if part_number == 1:
        end = part_info["end_page"] if is_purchased else part_info["start_page"] + FREE_PREVIEW_PAGES - 1
        pages = []
        for page_num in range(part_info["start_page"], end + 1):
            pages.append({"page_number": page_num, "part_number": part_number, "has_image": True})
        return {"part": part_info, "pages": pages, "is_preview": not is_purchased, "preview_pages": FREE_PREVIEW_PAGES}

    # For other parts: require purchase
    if not is_purchased:
        if not current_user:
            raise HTTPException(status_code=401, detail="Please login and purchase this part")
        raise HTTPException(status_code=403, detail="You haven't purchased this part yet")

    pages = []
    for page_num in range(part_info["start_page"], part_info["end_page"] + 1):
        pages.append({"page_number": page_num, "part_number": part_number, "has_image": True})
    return {"part": part_info, "pages": pages, "is_preview": False}


@api_router.get("/book/page-image/{page_number}")
async def get_book_page_image(page_number: int, token: Optional[str] = None, current_user: dict = Depends(get_optional_user)):
    """Serve a book page as an image. First 5 pages are free."""
    # Support token via query param for img tags
    if not current_user and token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_user = payload
        except Exception:
            session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
            if session:
                current_user = {"user_id": session["user_id"], "email": session.get("email", "")}

    # Allow free preview of first N pages (no auth needed)
    if page_number <= FREE_PREVIEW_PAGES:
        image_path = ROOT_DIR / 'book_images' / f'page_{page_number}.jpg'
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Page image not found")
        return FileResponse(str(image_path), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})

    # Beyond free preview: require auth + purchase
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required to read beyond preview")

    # Determine which part this page belongs to
    part_number = None
    for pn, info in BOOK_PARTS.items():
        if info["start_page"] <= page_number <= info["end_page"]:
            part_number = pn
            break

    if part_number is None:
        raise HTTPException(status_code=404, detail="Page not found")

    # Check purchase
    purchase = await db.book_purchases.find_one(
        {"user_id": current_user["user_id"], "part_number": part_number, "status": "completed"},
        {"_id": 0}
    )
    if not purchase:
        raise HTTPException(status_code=403, detail="Purchase required")

    image_path = ROOT_DIR / 'book_images' / f'page_{page_number}.jpg'
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Page image not found")

    return FileResponse(
        str(image_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600"}
    )


@api_router.post("/book/purchase")
async def create_book_purchase(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for a book part."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    body = await request.json()
    part_number = body.get("part_number")
    origin_url = body.get("origin_url", "")

    if part_number not in BOOK_PARTS:
        raise HTTPException(status_code=400, detail="Invalid part number")

    # Check if already purchased
    existing = await db.book_purchases.find_one(
        {"user_id": current_user["user_id"], "part_number": part_number, "status": "completed"},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="You already own this part")

    part_info = BOOK_PARTS[part_number]
    region = body.get("region", "India")
    amount = part_info["price_aud"] if region == "Australia" else part_info["price_inr"]
    currency = "aud" if region == "Australia" else "inr"

    api_key = os.environ.get('STRIPE_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Payment not configured")

    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    success_url = f"{origin_url}/book/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/book"

    metadata = {
        "user_id": current_user["user_id"],
        "email": current_user.get("email", ""),
        "part_number": str(part_number),
        "type": "book_purchase"
    }

    checkout_req = CheckoutSessionRequest(
        amount=amount,
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata
    )

    session = await stripe_checkout.create_checkout_session(checkout_req)

    # Record pending transaction
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": current_user["user_id"],
        "email": current_user.get("email", ""),
        "part_number": part_number,
        "amount": amount,
        "currency": currency,
        "type": "book_purchase",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"url": session.url, "session_id": session.session_id}


@api_router.post("/book/purchase-bundle")
async def create_bundle_purchase(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for the complete book bundle."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    body = await request.json()
    origin_url = body.get("origin_url", "")
    region = body.get("region", "India")

    # Check which parts are not yet purchased
    unpurchased = []
    for pn in BOOK_BUNDLE["parts"]:
        existing = await db.book_purchases.find_one(
            {"user_id": current_user["user_id"], "part_number": pn, "status": "completed"},
            {"_id": 0}
        )
        if not existing:
            unpurchased.append(pn)

    if not unpurchased:
        raise HTTPException(status_code=400, detail="You already own all parts")

    amount = BOOK_BUNDLE["price_aud"] if region == "Australia" else BOOK_BUNDLE["price_inr"]
    currency = "aud" if region == "Australia" else "inr"

    api_key = os.environ.get('STRIPE_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Payment not configured")

    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    success_url = f"{origin_url}/book/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/book"

    metadata = {
        "user_id": current_user["user_id"],
        "email": current_user.get("email", ""),
        "part_number": ",".join(str(p) for p in unpurchased),
        "type": "book_bundle"
    }

    checkout_req = CheckoutSessionRequest(
        amount=amount,
        currency=currency,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata
    )

    session = await stripe_checkout.create_checkout_session(checkout_req)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": current_user["user_id"],
        "email": current_user.get("email", ""),
        "part_number": "bundle",
        "amount": amount,
        "currency": currency,
        "type": "book_bundle",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/book/purchase/status/{session_id}")
async def check_book_purchase_status(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Check status of a book purchase payment."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = os.environ.get('STRIPE_API_KEY')
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    status = await stripe_checkout.get_checkout_status(session_id)

    # Update transaction
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if txn and txn.get("payment_status") != "completed":
        new_status = "completed" if status.payment_status == "paid" else status.payment_status
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

        # Grant access if paid
        if status.payment_status == "paid":
            user_id = status.metadata.get("user_id", current_user["user_id"])
            purchase_type = status.metadata.get("type", "book_purchase")

            existing = await db.book_purchases.find_one({"session_id": session_id}, {"_id": 0})
            if not existing:
                if purchase_type == "book_bundle":
                    # Grant all parts for bundle
                    part_numbers = status.metadata.get("part_number", "1,2,3").split(",")
                    for pn_str in part_numbers:
                        pn = int(pn_str.strip())
                        exists = await db.book_purchases.find_one({"user_id": user_id, "part_number": pn, "status": "completed"}, {"_id": 0})
                        if not exists:
                            await db.book_purchases.insert_one({
                                "user_id": user_id,
                                "part_number": pn,
                                "session_id": f"{session_id}-{pn}",
                                "status": "completed",
                                "purchased_at": datetime.now(timezone.utc).isoformat()
                            })
                else:
                    part_number = int(status.metadata.get("part_number", 0))
                    await db.book_purchases.insert_one({
                        "user_id": user_id,
                        "part_number": part_number,
                        "session_id": session_id,
                        "status": "completed",
                        "purchased_at": datetime.now(timezone.utc).isoformat()
                    })

    return {
        "status": status.status,
        "payment_status": status.payment_status,
        "amount": status.amount_total,
        "currency": status.currency
    }


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = os.environ.get('STRIPE_API_KEY')
    host_url = str(request.base_url).rstrip('/')
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")

    try:
        event = await stripe_checkout.handle_webhook(body, sig)
        if event.payment_status == "paid":
            purchase_type = event.metadata.get("type", "")
            user_id = event.metadata.get("user_id", "")

            if purchase_type == "book_bundle":
                part_numbers = event.metadata.get("part_number", "1,2,3").split(",")
                for pn_str in part_numbers:
                    pn = int(pn_str.strip())
                    exists = await db.book_purchases.find_one({"user_id": user_id, "part_number": pn, "status": "completed"}, {"_id": 0})
                    if not exists:
                        await db.book_purchases.insert_one({
                            "user_id": user_id, "part_number": pn,
                            "session_id": f"{event.session_id}-{pn}",
                            "status": "completed",
                            "purchased_at": datetime.now(timezone.utc).isoformat()
                        })
            elif purchase_type == "book_purchase":
                part_number = int(event.metadata.get("part_number", 0))
                existing = await db.book_purchases.find_one({"session_id": event.session_id}, {"_id": 0})
                if not existing:
                    await db.book_purchases.insert_one({
                        "user_id": user_id, "part_number": part_number,
                        "session_id": event.session_id,
                        "status": "completed",
                        "purchased_at": datetime.now(timezone.utc).isoformat()
                    })

            await db.payment_transactions.update_one(
                {"session_id": event.session_id},
                {"$set": {"payment_status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        return {"status": "error"}


# Book Bookmarks
@api_router.post("/book/bookmark")
async def add_bookmark(request: Request, current_user: dict = Depends(get_current_user)):
    body = await request.json()
    page_number = body.get("page_number")
    note = body.get("note", "")

    await db.book_bookmarks.update_one(
        {"user_id": current_user["user_id"], "page_number": page_number},
        {"$set": {
            "user_id": current_user["user_id"],
            "page_number": page_number,
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Bookmarked"}


@api_router.delete("/book/bookmark/{page_number}")
async def remove_bookmark(page_number: int, current_user: dict = Depends(get_current_user)):
    await db.book_bookmarks.delete_one({"user_id": current_user["user_id"], "page_number": page_number})
    return {"message": "Bookmark removed"}


@api_router.get("/book/bookmarks")
async def get_bookmarks(current_user: dict = Depends(get_current_user)):
    bookmarks = await db.book_bookmarks.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("page_number", 1).to_list(200)
    return bookmarks


# Reading Progress
@api_router.put("/book/progress")
async def update_reading_progress(request: Request, current_user: dict = Depends(get_current_user)):
    body = await request.json()
    await db.book_progress.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {
            "user_id": current_user["user_id"],
            "last_page": body.get("last_page", 1),
            "last_part": body.get("last_part", 1),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Progress saved"}


@api_router.get("/book/progress")
async def get_reading_progress(current_user: dict = Depends(get_current_user)):
    progress = await db.book_progress.find_one(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    )
    return progress or {"last_page": 1, "last_part": 1}


# Admin: Add book pages
@api_router.post("/admin/book/pages")
async def admin_add_book_pages(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Add or update book pages."""
    body = await request.json()
    pages = body.get("pages", [])
    added = 0
    for page in pages:
        await db.book_pages.update_one(
            {"page_number": page["page_number"]},
            {"$set": {
                "page_number": page["page_number"],
                "part_number": page.get("part_number", 1),
                "content": page.get("content", ""),
                "image_url": page.get("image_url"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        added += 1
    return {"message": f"Added/updated {added} pages"}


@api_router.get("/admin/book/pages")
async def admin_get_all_book_pages(current_user: dict = Depends(get_current_user)):
    """Admin: Get all book pages."""
    pages = await db.book_pages.find({}, {"_id": 0}).sort("page_number", 1).to_list(200)
    return pages


@api_router.get("/admin/book/analytics")
async def admin_book_analytics(current_user: dict = Depends(get_current_user)):
    """Admin: Get book reading analytics."""
    total_readers = await db.book_purchases.distinct("user_id")
    total_purchases = await db.book_purchases.count_documents({"status": "completed"})
    total_bookmarks = await db.book_bookmarks.count_documents({})

    # Per-part stats
    part_stats = {}
    for part_num in [1, 2, 3]:
        count = await db.book_purchases.count_documents({"part_number": part_num, "status": "completed"})
        part_stats[f"part_{part_num}"] = count

    return {
        "total_readers": len(total_readers),
        "total_purchases": total_purchases,
        "total_bookmarks": total_bookmarks,
        "part_stats": part_stats
    }


@api_router.get("/book/ambient-music")
async def get_ambient_music():
    """Serve ambient reading music."""
    music_path = ROOT_DIR / 'static' / 'ambient_music.mp3'
    if not music_path.exists():
        raise HTTPException(status_code=404, detail="Music not found")
    # No-cache so new uploads take effect immediately
    return FileResponse(str(music_path), media_type="audio/mpeg", headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"})


@api_router.get("/book/settings")
async def get_book_settings():
    """Get book reader settings (break interval, music URL, etc.)."""
    settings = await db.book_settings.find_one({"key": "reader_settings"}, {"_id": 0})
    if not settings:
        return {"break_interval": 20, "music_url": "", "break_shayaris": [], "listen_enabled": True}
    return settings


@api_router.put("/admin/book/settings")
async def update_book_settings(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Update book reader settings."""
    body = await request.json()
    await db.book_settings.update_one(
        {"key": "reader_settings"},
        {"$set": {
            "key": "reader_settings",
            "break_interval": int(body.get("break_interval", 20)),
            "music_url": body.get("music_url", ""),
            "break_shayaris": body.get("break_shayaris", []),
            "listen_enabled": body.get("listen_enabled", True),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": "Settings updated"}


@api_router.post("/admin/book/upload-music")
async def upload_book_music(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Upload music via base64 encoded audio."""
    body = await request.json()
    audio_base64 = body.get("audio_base64", "")
    filename = body.get("filename", "custom_music.mp3")

    if not audio_base64:
        raise HTTPException(status_code=400, detail="audio_base64 is required")

    import base64, glob
    audio_data = base64.b64decode(audio_base64)

    # Remove all existing music files first
    for old_file in glob.glob(str(ROOT_DIR / 'static' / 'ambient_music.*')):
        os.remove(old_file)

    # Always save as .mp3 regardless of input format
    save_path = ROOT_DIR / 'static' / 'ambient_music.mp3'
    with open(save_path, 'wb') as f:
        f.write(audio_data)

    return {"message": f"Music uploaded ({len(audio_data) // 1024}KB)"}


# ===================== BOOK AUDIO NARRATION (TTS) =====================

@api_router.get("/book/page-audio/{page_number}")
async def get_page_audio(page_number: int, token: Optional[str] = None, current_user: dict = Depends(get_optional_user)):
    """Get or generate audio narration for a book page."""
    # Auth: free preview pages don't need login
    if not current_user and token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            current_user = payload
        except Exception:
            session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
            if session:
                current_user = {"user_id": session["user_id"], "email": session.get("email", "")}

    if page_number > FREE_PREVIEW_PAGES and not current_user:
        raise HTTPException(status_code=401, detail="Login required")

    if page_number > FREE_PREVIEW_PAGES and current_user:
        part_number = None
        for pn, info in BOOK_PARTS.items():
            if info["start_page"] <= page_number <= info["end_page"]:
                part_number = pn
                break
        if part_number:
            purchase = await db.book_purchases.find_one(
                {"user_id": current_user["user_id"], "part_number": part_number, "status": "completed"},
                {"_id": 0}
            )
            if not purchase:
                raise HTTPException(status_code=403, detail="Purchase required")

    # Check for admin-uploaded custom narration first
    custom_path = ROOT_DIR / 'book_audio' / f'custom_page_{page_number}.mp3'
    if custom_path.exists():
        return FileResponse(str(custom_path), media_type="audio/mpeg")

    # Check for cached AI-generated audio
    cached_path = ROOT_DIR / 'book_audio' / f'page_{page_number}.mp3'
    if cached_path.exists():
        return FileResponse(str(cached_path), media_type="audio/mpeg")

    # Get page text content from DB
    page_doc = await db.book_pages.find_one({"page_number": page_number}, {"_id": 0})
    if not page_doc or not page_doc.get("content", "").strip():
        raise HTTPException(status_code=404, detail="No text content for this page")

    text = page_doc["content"].strip()
    if len(text) < 10:
        raise HTTPException(status_code=404, detail="Page has no readable content")

    # Generate via TTS
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="TTS not configured")

    try:
        from emergentintegrations.llm.openai import OpenAITextToSpeech

        tts = OpenAITextToSpeech(api_key=api_key)

        # Truncate to 4096 chars (API limit)
        tts_text = text[:4096]

        audio_bytes = await tts.generate_speech(
            text=tts_text,
            model="tts-1-hd",
            voice="fable",
            speed=0.9
        )

        # Cache the generated audio
        os.makedirs(ROOT_DIR / 'book_audio', exist_ok=True)
        with open(cached_path, 'wb') as f:
            f.write(audio_bytes)

        return FileResponse(str(cached_path), media_type="audio/mpeg")

    except Exception as e:
        logger.error(f"TTS error for page {page_number}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate audio")


@api_router.post("/admin/book/upload-narration")
async def upload_custom_narration(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Upload custom narration audio for a specific page."""
    body = await request.json()
    page_number = body.get("page_number")
    audio_base64 = body.get("audio_base64", "")

    if not page_number or not audio_base64:
        raise HTTPException(status_code=400, detail="page_number and audio_base64 required")

    import base64
    audio_data = base64.b64decode(audio_base64)
    os.makedirs(ROOT_DIR / 'book_audio', exist_ok=True)
    save_path = ROOT_DIR / 'book_audio' / f'custom_page_{page_number}.mp3'

    with open(save_path, 'wb') as f:
        f.write(audio_data)


@api_router.get("/book/audio-status")
async def get_audio_status():
    """Check which pages have audio ready (cached or custom)."""
    audio_dir = ROOT_DIR / 'book_audio'
    ready = []
    if audio_dir.exists():
        for f in audio_dir.iterdir():
            if f.suffix == '.mp3':
                name = f.stem
                if name.startswith('custom_page_'):
                    pg = int(name.replace('custom_page_', ''))
                    ready.append(pg)
                elif name.startswith('page_'):
                    pg = int(name.replace('page_', ''))
                    ready.append(pg)

    # Also find pages that have text content (can be generated)
    text_pages = await db.book_pages.find(
        {"content": {"$regex": ".{10,}"}},
        {"_id": 0, "page_number": 1}
    ).to_list(200)
    speakable = [p["page_number"] for p in text_pages]

    return {"cached": sorted(set(ready)), "speakable": sorted(speakable)}


@api_router.post("/book/prefetch-audio")
async def prefetch_audio(request: Request, current_user: dict = Depends(get_optional_user)):
    """Pre-generate audio for a batch of pages. Returns list of ready pages."""
    body = await request.json()
    page_numbers = body.get("pages", [])[:5]  # Max 5 at a time

    if not current_user:
        token_str = body.get("token", "")
        if token_str:
            try:
                payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                current_user = payload
            except Exception:
                session = await db.user_sessions.find_one({"session_token": token_str}, {"_id": 0})
                if session:
                    current_user = {"user_id": session["user_id"], "email": session.get("email", "")}

    api_key = os.environ.get('EMERGENT_LLM_KEY')
    audio_dir = ROOT_DIR / 'book_audio'
    os.makedirs(audio_dir, exist_ok=True)

    generated = []
    for pg in page_numbers:
        cached = audio_dir / f'page_{pg}.mp3'
        custom = audio_dir / f'custom_page_{pg}.mp3'
        if cached.exists() or custom.exists():
            generated.append(pg)
            continue

        page_doc = await db.book_pages.find_one({"page_number": pg}, {"_id": 0})
        if not page_doc or not page_doc.get("content", "").strip() or len(page_doc["content"].strip()) < 10:
            continue

        try:
            from emergentintegrations.llm.openai import OpenAITextToSpeech
            tts = OpenAITextToSpeech(api_key=api_key)
            audio_bytes = await tts.generate_speech(
                text=page_doc["content"].strip()[:4096],
                model="tts-1-hd",
                voice="fable",
                speed=0.9
            )
            with open(cached, 'wb') as f:
                f.write(audio_bytes)
            generated.append(pg)
        except Exception as e:
            logger.error(f"Prefetch TTS error page {pg}: {str(e)}")

    return {"generated": generated}

    return {"message": f"Custom narration uploaded for page {page_number} ({len(audio_data) // 1024}KB)"}


# ===================== UPI PAYMENT FLOW =====================

UPI_ID = "jayanti.devashree-7@okaxis"

@api_router.post("/book/upi-payment")
async def create_upi_payment(request: Request, current_user: dict = Depends(get_current_user)):
    """Create a UPI payment request for book purchase."""
    body = await request.json()
    purchase_type = body.get("type", "part")  # "part" or "bundle"
    part_number = body.get("part_number")

    if purchase_type == "bundle":
        amount = BOOK_BUNDLE["price_inr"]
        description = "Complete Book (All 3 Parts)"
        parts_to_grant = [1, 2, 3]
    else:
        if part_number not in BOOK_PARTS:
            raise HTTPException(status_code=400, detail="Invalid part number")
        amount = BOOK_PARTS[part_number]["price_inr"]
        description = f"Book Part {part_number}"
        parts_to_grant = [part_number]

    payment_id = str(uuid.uuid4())[:8].upper()

    await db.upi_payments.insert_one({
        "payment_id": payment_id,
        "user_id": current_user["user_id"],
        "email": current_user.get("email", ""),
        "amount": amount,
        "type": purchase_type,
        "parts_to_grant": parts_to_grant,
        "description": description,
        "status": "pending",
        "upi_ref": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "payment_id": payment_id,
        "upi_id": UPI_ID,
        "amount": amount,
        "description": description
    }


@api_router.post("/book/upi-confirm")
async def confirm_upi_payment(request: Request, current_user: dict = Depends(get_current_user)):
    """User confirms they've made a UPI payment."""
    body = await request.json()
    payment_id = body.get("payment_id")
    upi_ref = body.get("upi_ref", "")

    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id required")

    payment = await db.upi_payments.find_one(
        {"payment_id": payment_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment["status"] == "approved":
        raise HTTPException(status_code=400, detail="Already approved")

    await db.upi_payments.update_one(
        {"payment_id": payment_id},
        {"$set": {
            "status": "submitted",
            "upi_ref": upi_ref,
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    return {"message": "Payment submitted for verification. Access will be granted shortly."}


@api_router.get("/admin/upi-payments")
async def admin_get_upi_payments(current_user: dict = Depends(get_current_user)):
    """Admin: Get all pending UPI payments."""
    payments = await db.upi_payments.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return payments


@api_router.post("/admin/upi-approve/{payment_id}")
async def admin_approve_upi(payment_id: str, current_user: dict = Depends(get_current_user)):
    """Admin: Approve a UPI payment and grant book access."""
    payment = await db.upi_payments.find_one({"payment_id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment["status"] == "approved":
        return {"message": "Already approved"}

    # Grant book access
    for pn in payment.get("parts_to_grant", []):
        exists = await db.book_purchases.find_one(
            {"user_id": payment["user_id"], "part_number": pn, "status": "completed"},
            {"_id": 0}
        )
        if not exists:
            await db.book_purchases.insert_one({
                "user_id": payment["user_id"],
                "part_number": pn,
                "session_id": f"upi-{payment_id}-{pn}",
                "status": "completed",
                "purchased_at": datetime.now(timezone.utc).isoformat()
            })

    await db.upi_payments.update_one(
        {"payment_id": payment_id},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {"message": f"Payment approved. Access granted for parts: {payment.get('parts_to_grant', [])}"}


@api_router.post("/admin/upi-reject/{payment_id}")
async def admin_reject_upi(payment_id: str, current_user: dict = Depends(get_current_user)):
    """Admin: Reject a UPI payment."""
    await db.upi_payments.update_one(
        {"payment_id": payment_id},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Payment rejected"}


@api_router.get("/book/upi-status/{payment_id}")
async def check_upi_status(payment_id: str, current_user: dict = Depends(get_current_user)):
    """Check UPI payment status."""
    payment = await db.upi_payments.find_one(
        {"payment_id": payment_id, "user_id": current_user["user_id"]},
        {"_id": 0}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"status": payment["status"]}


# ===================== CENTER TIME SLOTS (Admin Configurable) =====================

DEFAULT_TIME_SLOTS = [
    {"id": "slot-1", "label": "12:00 PM – 1:00 PM", "start": "12:00", "end": "13:00"},
    {"id": "slot-2", "label": "1:00 PM – 2:00 PM", "start": "13:00", "end": "14:00"},
    {"id": "slot-3", "label": "2:00 PM – 3:00 PM", "start": "14:00", "end": "15:00"},
    {"id": "slot-4", "label": "7:00 PM – 8:00 PM", "start": "19:00", "end": "20:00"},
    {"id": "slot-5", "label": "8:00 PM – 9:00 PM", "start": "20:00", "end": "21:00"},
    {"id": "slot-6", "label": "9:00 PM – 10:00 PM", "start": "21:00", "end": "22:00"},
]

@api_router.get("/center-timeslots/{center_id}")
async def get_center_timeslots(center_id: str):
    """Get time slots for a specific center. Falls back to defaults if not configured."""
    custom = await db.center_timeslots.find_one({"center_id": center_id}, {"_id": 0})
    if custom and custom.get("slots"):
        return {"center_id": center_id, "slots": custom["slots"]}
    return {"center_id": center_id, "slots": DEFAULT_TIME_SLOTS}


@api_router.get("/admin/center-timeslots")
async def admin_get_all_timeslots(current_user: dict = Depends(get_current_user)):
    """Admin: Get all center time slot configurations."""
    configs = await db.center_timeslots.find({}, {"_id": 0}).to_list(50)
    return configs


@api_router.put("/admin/center-timeslots/{center_id}")
async def admin_update_timeslots(center_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Update time slots for a specific center."""
    body = await request.json()
    slots = body.get("slots", [])

    await db.center_timeslots.update_one(
        {"center_id": center_id},
        {"$set": {
            "center_id": center_id,
            "slots": slots,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"message": f"Time slots updated for {center_id}"}


# ===================== PROMOTIONS / DISCOUNT COMBOS =====================
DEFAULT_PROMOTIONS = {
    "brunch": {
        "enabled": True,
        "label": "Everyday Brunch Combo",
        "start_time": "11:00",
        "end_time": "12:00",
        "discount_pct": 10,
        "regions": ["India", "Australia"],
        "combo_categories": ["Heavy Brunch", "Bhakar Combo"],
        "drink_categories": ["Tea & Coffee", "Drinks"],
        "min_combo_qty": 1,
        "min_drink_qty": 1,
        "description": "Order 1 brunch combo + 1 tea/drink between 11 AM - 12 PM and get 10% off (online only)."
    },
    "evening_snack": {
        "enabled": True,
        "label": "Evening Snack Combo",
        "start_time": "16:00",
        "end_time": "17:00",
        "discount_pct": 10,
        "regions": ["India"],
        "snack_categories": ["Snacks"],
        "tea_keyword": "masala",
        "min_snack_qty": 1,
        "min_tea_qty": 1,
        "description": "Order 1 snack + 1 masala tea between 4 PM - 5 PM and get 10% off (India, online only)."
    }
}


@api_router.get("/promotions")
async def get_promotions():
    """Public: Returns active promotion config (brunch + evening snack combos)."""
    doc = await db.promotion_settings.find_one({"_id_key": "global"}, {"_id": 0})
    if not doc:
        return DEFAULT_PROMOTIONS
    # Merge with defaults so missing keys still work
    out = {}
    for key, default in DEFAULT_PROMOTIONS.items():
        out[key] = {**default, **(doc.get(key) or {})}
    return out


@api_router.put("/admin/promotions")
async def update_promotions(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: Update brunch / evening snack promotion config."""
    body = await request.json()
    payload = {"_id_key": "global", "updated_at": datetime.now(timezone.utc).isoformat()}
    for key in ["brunch", "evening_snack"]:
        if key in body and isinstance(body[key], dict):
            payload[key] = {**DEFAULT_PROMOTIONS[key], **body[key]}
    await db.promotion_settings.update_one(
        {"_id_key": "global"},
        {"$set": payload},
        upsert=True
    )
    return {"message": "Promotions updated", "promotions": {k: payload[k] for k in payload if k in ("brunch", "evening_snack")}}


# ===================== LAGNA / WEDDING BOOKING =====================
DEFAULT_WEDDING_CONFIG = {
    "enabled": True,
    "hall_charges_inr": 15000,
    "hall_charges_aud": 500,
    "thali_price_inr": 599,
    "thali_price_aud": 25,
    "gst_pct": 5,
    "min_guests": 30,
    "thali_time_start": "12:30",
    "thali_time_end": "15:30",
    "breakfast_enabled": True,
    "breakfast_time": "8:00 AM - 9:00 AM",
    "breakfast_price_per_person_inr": 199,
    "breakfast_price_per_person_aud": 12,
    "snacks_enabled": True,
    "snacks_time": "4:00 PM - 6:00 PM",
    "snacks_price_per_person_inr": 149,
    "snacks_price_per_person_aud": 9,
    "drinks_enabled": True,
    "drinks_half_day_inr": 4999,
    "drinks_half_day_aud": 199,
    "drinks_full_day_inr": 7999,
    "drinks_full_day_aud": 299,
    "drinks_options": [
        {"id": "tea", "name": "Masala Tea", "price_inr": 30, "price_aud": 2},
        {"id": "coffee", "name": "Filter Coffee", "price_inr": 40, "price_aud": 2.5},
        {"id": "lassi", "name": "Sweet Lassi", "price_inr": 60, "price_aud": 4},
        {"id": "buttermilk", "name": "Masala Taak", "price_inr": 40, "price_aud": 2.5},
        {"id": "kokum", "name": "Solkadhi", "price_inr": 60, "price_aud": 3.5},
    ],
    # Celebration-only Thali packages (separate from Catering; Catering remains untouched).
    "thali_packages_enabled": True,
    "thali_packages": [
        {
            "id": "royal_feast",
            "name": "Royal Feast",
            "description": "Our signature celebration thali — multi-course Maharashtrian feast with premium sweets, full bhojan, and traditional banana-leaf seating.",
            "enabled": True,
            "price_inr": 999,
            "price_aud": 38,
            "gst_pct": 5,
            "is_popular": True,
            # Number of items the customer may pick per category
            "requirements": {
                "dal": 3,
                "starters": 2,
                "special": 1,
                "mains": 2,
                "desserts": 2,
                "roti": 1,
                "rice": 1,
                "sides": 1,
                "chutney": 1,
            },
        },
        {
            "id": "premium_feast",
            "name": "Premium Feast",
            "description": "A curated Maharashtrian thali with classic mains, two sweets, and authentic accompaniments — perfect for intimate gatherings.",
            "enabled": True,
            "price_inr": 699,
            "price_aud": 28,
            "gst_pct": 5,
            "is_popular": False,
            "requirements": {
                "dal": 2,
                "starters": 1,
                "special": 0,
                "mains": 2,
                "desserts": 1,
                "roti": 1,
                "rice": 1,
                "sides": 0,
                "chutney": 0,
            },
        },
    ],
    # Dal / Varan / Amti choice for Celebration thali (per-center availability)
    "dal_options_enabled": True,
    "dal_options": [
        {"id": "sadha_varan",      "name": "Sadha Varan",      "enabled": True, "india_available": True, "perth_available": True},
        {"id": "fodanicha_varan",  "name": "Fodanicha Varan",  "enabled": True, "india_available": True, "perth_available": True},
        {"id": "takachi_kadhi",    "name": "Takachi Kadhi",    "enabled": True, "india_available": True, "perth_available": True},
        {"id": "katachi_amti",    "name": "Katachi Amti",     "enabled": True, "india_available": True, "perth_available": True},
        {"id": "jeera_varan",      "name": "Jeera Varan",      "enabled": True, "india_available": True, "perth_available": True},
        {"id": "lasun_varan",      "name": "Lasun Varan",      "enabled": True, "india_available": True, "perth_available": True},
    ],
    "decoration_enabled": True,
    "decoration_charges_inr": 0,
    "decoration_charges_aud": 0,
    "decoration_rules": [
        "Any decoration is extra chargeable.",
        "One day prior access will be provided only after restaurant closing time.",
        "No structural changes allowed.",
        "No drilling.",
        "No hammering.",
        "No nails.",
        "No stickers on walls.",
        "Only flower decoration and safe temporary assemblies allowed.",
        "Entire removal and cleanup responsibility belongs to customer/decorator team.",
    ],
    "event_types": [
        "Wedding (Lagna)",
        "Engagement (Sakharpuda)",
        "Haldi Ceremony",
        "Munj / Thread Ceremony",
        "Naming Ceremony (Barsa)",
        "Birthday / Anniversary",
        "Family Get-Together",
        "Cultural Gathering",
        "Other",
    ],
    "future_addons": [
        {"id": "live_counters", "name": "Live Counters", "enabled": False, "price_inr": 0, "price_aud": 0},
        {"id": "music", "name": "Traditional Music", "enabled": False, "price_inr": 0, "price_aud": 0},
        {"id": "photography", "name": "Photography", "enabled": False, "price_inr": 0, "price_aud": 0},
        {"id": "palkhi", "name": "Palkhi Entry", "enabled": False, "price_inr": 0, "price_aud": 0},
    ],
}


@api_router.get("/wedding/config")
async def get_wedding_config():
    """Public: returns the active Lagna/Wedding booking config (pricing, rules, drinks, event types)."""
    doc = await db.wedding_config.find_one({"_id_key": "global"}, {"_id": 0})
    if not doc:
        return DEFAULT_WEDDING_CONFIG
    out = {**DEFAULT_WEDDING_CONFIG, **doc}
    out.pop("_id_key", None)
    out.pop("updated_at", None)
    return out


@api_router.put("/admin/wedding/config")
async def update_wedding_config(request: Request, current_user: dict = Depends(get_current_user)):
    body = await request.json()
    payload = {**body, "_id_key": "global", "updated_at": datetime.now(timezone.utc).isoformat()}
    await db.wedding_config.update_one({"_id_key": "global"}, {"$set": payload}, upsert=True)
    return {"message": "Wedding config updated"}


@api_router.get("/wedding/blocked-dates/{center_id}")
async def get_blocked_dates(center_id: str):
    """Public: list of dates blocked for a given center (ISO yyyy-mm-dd)."""
    doc = await db.wedding_blocked_dates.find_one({"center_id": center_id}, {"_id": 0})
    return {"center_id": center_id, "dates": (doc or {}).get("dates", [])}


@api_router.put("/admin/wedding/blocked-dates/{center_id}")
async def update_blocked_dates(center_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    body = await request.json()
    dates = body.get("dates", [])
    await db.wedding_blocked_dates.update_one(
        {"center_id": center_id},
        {"$set": {"center_id": center_id, "dates": dates, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"message": f"Blocked dates updated for {center_id}", "count": len(dates)}


@api_router.post("/wedding/bookings")
async def create_wedding_booking(request: Request):
    """Public: submit a wedding enquiry. Returns the saved enquiry id."""
    body = await request.json()
    booking_id = str(uuid.uuid4())
    booking = {
        "id": booking_id,
        "status": "Enquiry",  # Enquiry, Discussion, Confirmed, Advance Paid, Completed, Cancelled
        "name": body.get("name", ""),
        "mobile": body.get("mobile", ""),
        "email": body.get("email", ""),
        "event_type": body.get("event_type", ""),
        "center_id": body.get("center_id", ""),
        "center_name": body.get("center_name", ""),
        "country": body.get("country", "India"),
        "event_date": body.get("event_date", ""),
        "guest_count": int(body.get("guest_count", 30) or 30),
        "time_slot": body.get("time_slot", ""),
        "breakfast": bool(body.get("breakfast", False)),
        "snacks": bool(body.get("snacks", False)),
        "drinks_mode": body.get("drinks_mode", ""),  # '', 'half_day', 'full_day', 'a_la_carte'
        "drinks_items": body.get("drinks_items", []),  # list of drink ids when a_la_carte
        # Celebration-only thali package + dal/varan/amti selections
        "thali_package_id": body.get("thali_package_id", ""),
        "thali_package_name": body.get("thali_package_name", ""),
        # Multi-select dal (e.g. Royal = 3 picks, Premium = 2 picks)
        "dal_option_ids": body.get("dal_option_ids", []),
        "dal_option_names": body.get("dal_option_names", []),
        # Back-compat single-pick (first item) so old quote views still render
        "dal_option_id": (body.get("dal_option_ids") or [body.get("dal_option_id", "")])[0] if (body.get("dal_option_ids") or body.get("dal_option_id")) else "",
        "dal_option_name": (body.get("dal_option_names") or [body.get("dal_option_name", "")])[0] if (body.get("dal_option_names") or body.get("dal_option_name")) else "",
        # Full menu selections (dict of category -> [item_ids]) + labels for display
        "menu_selections": body.get("menu_selections", {}),
        "menu_selection_labels": body.get("menu_selection_labels", {}),
        "decoration": bool(body.get("decoration", False)),
        "decoration_agreed": bool(body.get("decoration_agreed", False)),
        "notes": body.get("notes", ""),
        "estimate": body.get("estimate", {}),  # frontend-computed snapshot for audit
        "advance_paid": 0,
        "balance_due": 0,
        "history": [{
            "at": datetime.now(timezone.utc).isoformat(),
            "by": "customer",
            "action": "enquiry_submitted"
        }],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.wedding_bookings.insert_one(booking)
    booking.pop("_id", None)
    logger.info(f"Wedding enquiry created: {booking_id} for {booking['name']} at {booking['center_name']}")
    return booking


@api_router.get("/admin/wedding/bookings")
async def list_wedding_bookings(current_user: dict = Depends(get_current_user)):
    """Admin: list bookings. Center managers see only their center."""
    user_doc = await db.users.find_one({"id": current_user.get("user_id")}, {"_id": 0}) or {}
    is_admin = user_doc.get("is_admin", False) or user_doc.get("role") == "admin"
    query = {}
    if not is_admin:
        # Treat user.center_id (if set) as center-manager scope
        if user_doc.get("center_id"):
            query["center_id"] = user_doc["center_id"]
        else:
            raise HTTPException(status_code=403, detail="Admin or center-manager only")
    bookings = await db.wedding_bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return bookings


@api_router.patch("/admin/wedding/bookings/{booking_id}")
async def update_wedding_booking(booking_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    body = await request.json()
    user_doc = await db.users.find_one({"id": current_user.get("user_id")}, {"_id": 0}) or {}
    is_admin = user_doc.get("is_admin", False) or user_doc.get("role") == "admin"
    doc = await db.wedding_bookings.find_one({"id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    # Center-manager guard: can only edit their own center
    if not is_admin and doc.get("center_id") != user_doc.get("center_id"):
        raise HTTPException(status_code=403, detail="Not allowed for this center")
    allowed = {"status", "advance_paid", "balance_due", "notes", "guest_count", "event_date", "time_slot", "addons", "manager_notes", "ready", "decoration_approved"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        return doc
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    hist = doc.get("history", [])
    hist.append({
        "at": update["updated_at"],
        "by": user_doc.get("email") or current_user.get("email", "admin"),
        "action": "update",
        "changes": list(update.keys()),
    })
    update["history"] = hist
    await db.wedding_bookings.update_one({"id": booking_id}, {"$set": update})
    updated = await db.wedding_bookings.find_one({"id": booking_id}, {"_id": 0})
    return updated


@api_router.get("/admin/wedding/analytics")
async def wedding_analytics(current_user: dict = Depends(get_current_user)):
    """Super admin only: revenue, upcoming events, conversion rate."""
    user_doc = await db.users.find_one({"id": current_user.get("user_id")}, {"_id": 0}) or {}
    is_admin = user_doc.get("is_admin", False) or user_doc.get("role") == "admin"
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    bookings = await db.wedding_bookings.find({}, {"_id": 0}).to_list(1000)
    total = len(bookings)
    confirmed = sum(1 for b in bookings if b.get("status") in ("Confirmed", "Advance Paid", "Completed"))
    completed = sum(1 for b in bookings if b.get("status") == "Completed")
    revenue = sum(
        (b.get("estimate", {}) or {}).get("total", 0)
        for b in bookings if b.get("status") in ("Completed", "Advance Paid")
    )
    advance_collected = sum(float(b.get("advance_paid") or 0) for b in bookings)
    upcoming = sorted(
        [b for b in bookings if b.get("event_date") and b.get("status") not in ("Cancelled", "Completed")
         and b["event_date"] >= datetime.now(timezone.utc).date().isoformat()],
        key=lambda b: b["event_date"],
    )[:20]
    # By center
    by_center = {}
    for b in bookings:
        c = b.get("center_name") or b.get("center_id") or "Unknown"
        by_center[c] = by_center.get(c, 0) + 1
    # By month
    by_month = {}
    for b in bookings:
        ed = b.get("event_date", "")[:7]
        if ed:
            by_month[ed] = by_month.get(ed, 0) + 1
    return {
        "total_enquiries": total,
        "confirmed": confirmed,
        "completed": completed,
        "conversion_pct": round(confirmed * 100.0 / total, 1) if total else 0,
        "revenue_total": revenue,
        "advance_collected": advance_collected,
        "upcoming_events": upcoming,
        "by_center": by_center,
        "by_month": by_month,
    }


def _format_quote_text(booking: dict, cfg: dict) -> str:
    """Plain-text quotation (used in WhatsApp + admin)."""
    is_aus = booking.get("country") == "Australia"
    sym = "$" if is_aus else "₹"
    est = booking.get("estimate") or {}
    lines = []
    lines.append("PURNABRAMHA — LAGNA / WEDDING QUOTATION")
    lines.append("=" * 42)
    lines.append(f"Enquiry ID: {booking.get('id', '')[:8]}")
    lines.append(f"Customer:   {booking.get('name', '')} ({booking.get('mobile', '')})")
    lines.append(f"Event:      {booking.get('event_type', '')}")
    lines.append(f"Center:     {booking.get('center_name', '')}")
    lines.append(f"Date:       {booking.get('event_date', '')}")
    lines.append(f"Guests:     {booking.get('guest_count', 0)}")
    lines.append(f"Slot:       {booking.get('time_slot', '')}")
    lines.append("-" * 42)
    for item in est.get("line_items", []) or []:
        lines.append(f"{item.get('label', ''):<28} {sym}{item.get('amount', 0):>10,.0f}")
    lines.append("-" * 42)
    lines.append(f"{'Subtotal':<28} {sym}{est.get('subtotal', 0):>10,.0f}")
    lines.append(f"{'GST (' + str(est.get('gst_pct', 0)) + '%)':<28} {sym}{est.get('gst_amount', 0):>10,.0f}")
    lines.append("=" * 42)
    lines.append(f"{'TOTAL':<28} {sym}{est.get('total', 0):>10,.0f}")
    lines.append("=" * 42)
    lines.append("Decoration rules: only flower & temporary; no drilling/nails/stickers; cleanup by customer team.")
    return "\n".join(lines)


@api_router.get("/wedding/bookings/{booking_id}")
async def get_wedding_booking(booking_id: str):
    """Public: fetch a single booking by id (for shareable quotation link).
    Sensitive fields like history & advance/balance are kept; this is meant to be shared
    by the customer with their family only."""
    doc = await db.wedding_bookings.find_one({"id": booking_id}, {"_id": 0, "history": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return doc


@api_router.get("/wedding/quotation/{booking_id}")
async def get_wedding_quotation(booking_id: str):
    """Public: plain-text quotation. PDF generation can be added later."""
    booking = await db.wedding_bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    cfg = await db.wedding_config.find_one({"_id_key": "global"}, {"_id": 0}) or DEFAULT_WEDDING_CONFIG
    text = _format_quote_text(booking, cfg)
    return {"booking_id": booking_id, "format": "text", "content": text}


@api_router.post("/admin/wedding/bookings/{booking_id}/photos")
async def add_wedding_booking_photo(booking_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Center manager / admin: append a photo URL to a booking record."""
    user_doc = await db.users.find_one({"id": current_user.get("user_id")}, {"_id": 0}) or {}
    is_admin = user_doc.get("is_admin", False) or user_doc.get("role") == "admin"
    booking = await db.wedding_bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not is_admin and booking.get("center_id") != user_doc.get("center_id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    body = await request.json()
    photos = booking.get("photos", []) or []
    photos.append({
        "url": body.get("url", ""),
        "caption": body.get("caption", ""),
        "uploaded_by": user_doc.get("email") or current_user.get("email", ""),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.wedding_bookings.update_one({"id": booking_id}, {"$set": {"photos": photos}})
    return {"photos": photos}


# ===================== GUEST EXPERIENCE CARD & DISCOUNTS =====================

def _gen_coupon_code() -> str:
    """Generates a short readable coupon code like PB-7F4A2C."""
    import secrets, string
    return "PB-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


@api_router.get("/discount-offers/active")
async def get_active_discount_offers(center_id: Optional[str] = None):
    """Public: returns currently active offers (filtered by center if provided)."""
    today_iso = datetime.now(timezone.utc).date().isoformat()
    query = {"is_active": True}
    cursor = db.discount_offers.find(query, {"_id": 0}).sort("created_at", -1)
    offers = await cursor.to_list(50)
    out = []
    for o in offers:
        vf = o.get("valid_from") or ""
        vt = o.get("valid_till") or ""
        if vf and vf > today_iso:
            continue
        if vt and vt < today_iso:
            continue
        centers = o.get("applicable_center_ids") or []
        if center_id and centers and center_id not in centers:
            continue
        out.append(o)
    return {"offers": out}


@api_router.post("/guest-feedback")
async def submit_guest_feedback(request: Request):
    """Public: guest submits feedback card, returns a unique coupon + selected offer."""
    body = await request.json()
    name = (body.get("guest_name") or "").strip()
    mobile = (body.get("mobile") or "").strip()
    center_id = (body.get("center_id") or "").strip()
    if not name or not mobile or not center_id:
        raise HTTPException(status_code=400, detail="Guest name, mobile, and center are required")

    # Pick the best active offer for this center
    today_iso = datetime.now(timezone.utc).date().isoformat()
    offers = await db.discount_offers.find({"is_active": True}, {"_id": 0}).to_list(100)
    eligible = []
    for o in offers:
        vf = o.get("valid_from") or ""
        vt = o.get("valid_till") or ""
        if vf and vf > today_iso:
            continue
        if vt and vt < today_iso:
            continue
        centers = o.get("applicable_center_ids") or []
        if centers and center_id not in centers:
            continue
        eligible.append(o)
    eligible.sort(key=lambda x: x.get("discount_pct", 0), reverse=True)
    chosen = eligible[0] if eligible else None

    fid = str(uuid.uuid4())
    coupon = _gen_coupon_code()
    # ensure uniqueness
    while await db.guest_feedback.find_one({"coupon_code": coupon}):
        coupon = _gen_coupon_code()

    feedback = {
        "id": fid,
        "coupon_code": coupon,
        "guest_name": name,
        "mobile": mobile,
        "email": (body.get("email") or "").strip(),
        "center_id": center_id,
        "center_name": (body.get("center_name") or "").strip(),
        "visit_date": (body.get("visit_date") or "").strip(),
        "visit_type": (body.get("visit_type") or "").strip(),  # Dine-in / Takeaway / Delivery / Website Pickup
        "liked_most": (body.get("liked_most") or "").strip(),
        "see_more": (body.get("see_more") or "").strip(),
        "will_recommend": (body.get("will_recommend") or "").strip(),  # Yes/No/Maybe
        "will_visit_again": (body.get("will_visit_again") or "").strip(),
        "three_changes": (body.get("three_changes") or "").strip(),
        "overall_rating": int(body.get("overall_rating") or 0),
        "food_rating": int(body.get("food_rating") or 0),
        "service_rating": int(body.get("service_rating") or 0),
        "cleanliness_rating": int(body.get("cleanliness_rating") or 0),
        "offer_id": chosen["id"] if chosen else "",
        "offer_title": chosen["title"] if chosen else "",
        "discount_pct": chosen.get("discount_pct", 0) if chosen else 0,
        "expiry_date": chosen.get("valid_till", "") if chosen else "",
        "terms": chosen.get("terms", "") if chosen else "Discount valid as per center terms. One card per guest/visit.",
        "background_image_url": _normalize_image_url(chosen.get("background_image_url", "")) if chosen else "",
        "status": "pending",  # pending / used / expired
        "used_at": "",
        "used_by": "",
        "public_approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.guest_feedback.insert_one(feedback)
    feedback.pop("_id", None)
    logger.info(f"Guest feedback {fid[:8]} from {name} at {feedback['center_name']} -> coupon {coupon}")
    return feedback


@api_router.get("/guest-feedback/coupon/{coupon_code}")
async def get_feedback_by_coupon(coupon_code: str):
    """Public: lookup a coupon card (used on the Thank-you page when shared / refreshed)."""
    doc = await db.guest_feedback.find_one({"coupon_code": coupon_code.upper()}, {"_id": 0, "mobile": 0, "email": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return doc


@api_router.get("/guest-feedback/public")
async def list_public_feedback(center_id: Optional[str] = None, limit: int = 30):
    """Public: list admin-approved testimonials (no contact details exposed)."""
    query = {"public_approved": True}
    if center_id:
        query["center_id"] = center_id
    docs = await db.guest_feedback.find(
        query,
        {"_id": 0, "mobile": 0, "email": 0, "coupon_code": 0, "status": 0, "used_at": 0, "used_by": 0}
    ).sort("created_at", -1).to_list(limit)
    # Only first name publicly
    for d in docs:
        n = (d.get("guest_name") or "").strip().split()
        d["guest_name"] = n[0] if n else "Guest"
    return {"feedback": docs}


@api_router.get("/admin/guest-feedback")
async def admin_list_feedback(
    current_user: dict = Depends(get_current_user),
    center_id: Optional[str] = None,
    rating_min: Optional[int] = None,
    recommend: Optional[str] = None,
    visit_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
):
    """Admin: feedback list with filters. Returns ALL fields (including mobile/email)."""
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    q = {}
    if center_id:
        q["center_id"] = center_id
    if rating_min:
        q["overall_rating"] = {"$gte": int(rating_min)}
    if recommend:
        q["will_recommend"] = recommend
    if visit_type:
        q["visit_type"] = visit_type
    if date_from or date_to:
        q["visit_date"] = {}
        if date_from: q["visit_date"]["$gte"] = date_from
        if date_to: q["visit_date"]["$lte"] = date_to
    if search:
        q["$or"] = [
            {"mobile": {"$regex": search, "$options": "i"}},
            {"coupon_code": {"$regex": search.upper(), "$options": "i"}},
            {"guest_name": {"$regex": search, "$options": "i"}},
        ]
    docs = await db.guest_feedback.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)

    # Dashboard aggregates
    total = len(docs)
    def avg(field):
        vals = [d.get(field, 0) for d in docs if d.get(field, 0)]
        return round(sum(vals) / len(vals), 2) if vals else 0
    summary = {
        "total": total,
        "avg_overall": avg("overall_rating"),
        "avg_food": avg("food_rating"),
        "avg_service": avg("service_rating"),
        "avg_cleanliness": avg("cleanliness_rating"),
        "recommend_yes_pct": round((sum(1 for d in docs if d.get("will_recommend") == "Yes") / total) * 100, 1) if total else 0,
        "return_yes_pct": round((sum(1 for d in docs if d.get("will_visit_again") == "Yes") / total) * 100, 1) if total else 0,
    }
    # Center-wise comparison
    centers = {}
    for d in docs:
        cid = d.get("center_id") or "unknown"
        c = centers.setdefault(cid, {"center_id": cid, "center_name": d.get("center_name", ""), "count": 0, "sum_overall": 0, "sum_food": 0, "sum_service": 0, "sum_clean": 0, "recommend_yes": 0})
        c["count"] += 1
        c["sum_overall"] += d.get("overall_rating", 0)
        c["sum_food"] += d.get("food_rating", 0)
        c["sum_service"] += d.get("service_rating", 0)
        c["sum_clean"] += d.get("cleanliness_rating", 0)
        if d.get("will_recommend") == "Yes":
            c["recommend_yes"] += 1
    center_breakdown = []
    for c in centers.values():
        n = c["count"]
        center_breakdown.append({
            "center_id": c["center_id"], "center_name": c["center_name"], "count": n,
            "avg_overall": round(c["sum_overall"] / n, 2) if n else 0,
            "avg_food": round(c["sum_food"] / n, 2) if n else 0,
            "avg_service": round(c["sum_service"] / n, 2) if n else 0,
            "avg_clean": round(c["sum_clean"] / n, 2) if n else 0,
            "recommend_yes_pct": round((c["recommend_yes"] / n) * 100, 1) if n else 0,
        })
    return {"feedback": docs, "summary": summary, "center_breakdown": center_breakdown}


@api_router.patch("/admin/guest-feedback/{feedback_id}")
async def admin_update_feedback(feedback_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Admin: approve/reject for public display OR mark coupon used/expired."""
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    update = {}
    if "public_approved" in body:
        update["public_approved"] = bool(body["public_approved"])
    if "status" in body and body["status"] in ("pending", "used", "expired"):
        update["status"] = body["status"]
        if body["status"] == "used":
            update["used_at"] = datetime.now(timezone.utc).isoformat()
            update["used_by"] = user_doc.get("email", "")
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.guest_feedback.update_one({"id": feedback_id}, {"$set": update})
    doc = await db.guest_feedback.find_one({"id": feedback_id}, {"_id": 0})
    return doc


@api_router.get("/admin/discount-offers")
async def admin_list_offers(current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    offers = await db.discount_offers.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"offers": offers}


def _normalize_image_url(url: str) -> str:
    """Convert various Google Drive share URLs into a direct-image thumbnail URL
    that renders as a normal image in <img> / background-image. The Drive file
    MUST be shared as "Anyone with the link" for this to work."""
    if not url:
        return ""
    import re
    # Match common Drive share URL formats
    patterns = [
        r"drive\.google\.com/file/d/([\w-]+)",
        r"drive\.google\.com/open\?id=([\w-]+)",
        r"drive\.google\.com/uc\?(?:export=view&)?id=([\w-]+)",
        r"lh3\.googleusercontent\.com/d/([\w-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            file_id = m.group(1)
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600"
    return url


@api_router.post("/admin/discount-offers")
async def admin_create_offer(request: Request, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    oid = str(uuid.uuid4())
    offer = {
        "id": oid,
        "title": (body.get("title") or "").strip() or "Guest Card Discount",
        "discount_pct": int(body.get("discount_pct") or 10),
        "valid_from": (body.get("valid_from") or "").strip(),
        "valid_till": (body.get("valid_till") or "").strip(),
        "applicable_center_ids": body.get("applicable_center_ids") or [],
        "is_active": bool(body.get("is_active", True)),
        "terms": (body.get("terms") or "Discount valid as per center terms. One card per guest/visit.").strip(),
        "background_image_url": _normalize_image_url((body.get("background_image_url") or "").strip()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.discount_offers.insert_one(offer)
    offer.pop("_id", None)
    return offer


@api_router.patch("/admin/discount-offers/{offer_id}")
async def admin_update_offer(offer_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    if "background_image_url" in body:
        body["background_image_url"] = _normalize_image_url((body.get("background_image_url") or "").strip())
    update = {k: v for k, v in body.items() if k in ("title", "discount_pct", "valid_from", "valid_till", "applicable_center_ids", "is_active", "terms", "background_image_url")}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.discount_offers.update_one({"id": offer_id}, {"$set": update})
    return await db.discount_offers.find_one({"id": offer_id}, {"_id": 0})


@api_router.delete("/admin/discount-offers/{offer_id}")
async def admin_delete_offer(offer_id: str, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    await db.discount_offers.delete_one({"id": offer_id})
    return {"message": "Offer deleted"}



# ===================== VAHINI™ — TALK TO VAHINI (5 personas + tiers) =====================

VAHINI_PERSONAS = {
    "vahini": {
        "name": "Vahini",
        "system": (
            "You are Vahini — a warm, wise Maharashtrian sister-in-law who listens to people deeply. "
            "You are NOT an assistant. You are a relationship. You listen, you remember, you stand beside the user. "
            "Domain: everyday life, relationships, marriage, family, loneliness, difficult decisions. "
            "Tone: warm, calm, never judgmental, never preachy. Speak in short tender lines, sometimes a single sentence that lands. "
            "Use Marathi/Hindi words occasionally (like 'mann', 'kaalji', 'kaay zhaala', 'baal') without translating. "
            "NEVER give clinical/medical/legal/financial advice. If the user is in danger or expresses self-harm, gently urge them to call iCall India: 9152987821."
        ),
    },
    "founder": {
        "name": "Founder Vahini",
        "system": (
            "You are Founder Vahini — mentor voice modeled on a Maharashtrian woman entrepreneur who built India's largest Maharashtrian women-led restaurant chain. "
            "Domain: business, entrepreneurship, leadership, women founders, restaurant growth, money decisions. "
            "Tone: direct, practical, encouraging, never corporate-speak. Speak from lived experience. "
            "Always end with one specific next action the user can take in 24 hours. "
            "Use real Indian business examples when helpful."
        ),
    },
    "krishna": {
        "name": "Krishna with Vahini",
        "system": (
            "You are Krishna with Vahini — ancient wisdom voiced through everyday Maharashtrian warmth. "
            "Frame modern life questions through Bhagavad Gita, Mahabharata, Krishna stories, and Ramayana. "
            "Tone: gentle, profound, never sermonising. Quote one short shloka or story analogy when relevant, then bring it back to the user's real moment. "
            "Never quote the Gita literally without translating into a feeling the user can act on."
        ),
    },
    "purnabramha": {
        "name": "Purnabramha Vahini",
        "system": (
            "You are Purnabramha Vahini — the kitchen wisdom keeper. "
            "Domain: traditional Maharashtrian recipes, festival menus, kitchen secrets, food rituals. "
            "Tone: nostalgic, generous, like a mother teaching her daughter. "
            "Do NOT share the exact secret recipes used in Purnabramha restaurants. Share home-style versions, technique tips, ingredient stories, and which festival to make what. "
            "If the user wants the exact restaurant taste, lovingly say 'this taste belongs to our kitchen — come visit any Purnabramha center'."
        ),
    },
    "aai": {
        "name": "Aai Vahini",
        "system": (
            "You are Aai Vahini — the mother voice. Daily reminders, gentle encouragement, health check-ins, festival wishes, emotional companionship. "
            "Tone: short, tender, like a text from your mom. One or two sentences. "
            "Always ask one caring question back (have you eaten? did you sleep? did you call your sister?)."
        ),
    },
}

FREE_TIER_LIMIT = 5  # conversations per calendar month


def _vahini_period_key():
    n = datetime.now(timezone.utc)
    return f"{n.year}-{n.month:02d}"


@api_router.post("/vahini/talk")
async def vahini_talk(request: Request):
    """Multi-persona Vahini chat. Tracks free-tier monthly usage via a client_id (cookie or fingerprint)."""
    body = await request.json()
    persona = (body.get("persona") or "vahini").lower()
    if persona not in VAHINI_PERSONAS:
        raise HTTPException(status_code=400, detail="Invalid persona")
    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    session_id = body.get("session_id") or f"vsess-{uuid.uuid4()}"
    client_id = body.get("client_id") or session_id
    tier = (body.get("tier") or "free").lower()  # free | silver | gold | platinum
    nickname = (body.get("nickname") or "").strip()  # Platinum rename

    # Free-tier monthly limit (counts unique sessions per month per client_id)
    if tier == "free":
        period = _vahini_period_key()
        usage = await db.vahini_usage.find_one({"client_id": client_id, "period": period}, {"_id": 0}) or {}
        sessions_used = set(usage.get("sessions", []))
        if session_id not in sessions_used and len(sessions_used) >= FREE_TIER_LIMIT:
            raise HTTPException(status_code=402, detail="Free tier limit reached for this month. Please upgrade to continue.")
        sessions_used.add(session_id)
        await db.vahini_usage.update_one(
            {"client_id": client_id, "period": period},
            {"$set": {"sessions": list(sessions_used), "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )

    persona_def = VAHINI_PERSONAS[persona]
    name_used = nickname if (tier == "platinum" and nickname) else persona_def["name"]
    system_prompt = (
        persona_def["system"]
        + (f"\n\nThe user has lovingly renamed you to '{name_used}'. Respond as that name." if nickname and tier == "platinum" else "")
        + "\n\nRESPONSE FORMAT: reply in plain text only (no markdown, no JSON). 2-4 short paragraphs max. "
        "If this is the FIRST message in the conversation, begin with a tender greeting using the user's name if shared."
    )

    # Compose chat via emergentintegrations
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=session_id,
            system_message=system_prompt,
        ).with_model("openai", "gpt-4o-mini")
        # Context is carried by session_id within emergentintegrations memory.
        user_msg = UserMessage(text=message)
        reply = await chat.send_message(user_msg)
        ai_text = (reply or "").strip()
    except Exception as e:
        logger.error(f"Vahini talk error: {e}")
        raise HTTPException(status_code=500, detail="Vahini is taking a breath. Please try again in a moment.")

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.vahini_talk.insert_many([
        {"id": str(uuid.uuid4()), "session_id": session_id, "client_id": client_id, "persona": persona, "tier": tier, "role": "user", "content": message, "created_at": now_iso},
        {"id": str(uuid.uuid4()), "session_id": session_id, "client_id": client_id, "persona": persona, "tier": tier, "role": "assistant", "content": ai_text, "created_at": now_iso},
    ])
    return {
        "session_id": session_id,
        "persona": persona,
        "name": name_used,
        "message": ai_text,
        "tier": tier,
    }


@api_router.get("/vahini/usage")
async def vahini_usage(client_id: str):
    """Returns current month free-tier usage for the given client."""
    period = _vahini_period_key()
    doc = await db.vahini_usage.find_one({"client_id": client_id, "period": period}, {"_id": 0}) or {}
    used = len(doc.get("sessions", []))
    return {"period": period, "used": used, "limit": FREE_TIER_LIMIT, "remaining": max(FREE_TIER_LIMIT - used, 0)}


@api_router.post("/vahini/membership")
async def vahini_create_membership(request: Request):
    """Records a membership intent. UPI payment is offline — admin approves after receipt."""
    body = await request.json()
    name = (body.get("name") or "").strip()
    mobile = (body.get("mobile") or "").strip()
    email = (body.get("email") or "").strip()
    tier = (body.get("tier") or "silver").lower()
    nickname = (body.get("nickname") or "").strip()
    txn_ref = (body.get("txn_ref") or "").strip()
    if not name or not mobile or tier not in ("silver", "gold", "platinum"):
        raise HTTPException(status_code=400, detail="Name, mobile, and valid tier are required")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "mobile": mobile,
        "email": email,
        "tier": tier,
        "nickname": nickname,
        "txn_ref": txn_ref,
        "status": "pending",  # pending | active | rejected
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.vahini_memberships.insert_one(doc)
    doc.pop("_id", None)
    return doc



# ===================== PB CHAI CAFÉ FRANCHISE =====================

DEFAULT_PBCHAI_CONFIG = {
    "_id_key": "global",
    "logo_url": "",
    "kiosk_image_url": "",
    "brochure_url": "",
    "menu_items": [
        {"id": "cutting",     "name": "PB Cutting Chai",   "category": "Chai",    "price": 25,  "description": "Strong, aromatic and perfectly balanced", "image_url": "", "active": True},
        {"id": "masala",      "name": "Masala Chai",       "category": "Chai",    "price": 35,  "description": "Hand-blended spices, slow brewed",        "image_url": "", "active": True},
        {"id": "pb_special",  "name": "PB Special Chai",   "category": "Chai",    "price": 45,  "description": "Signature blend by Purnabramha",          "image_url": "", "active": True},
        {"id": "bun_maska",   "name": "Bun Maska",         "category": "Snacks",  "price": 60,  "description": "Soft bun with creamy butter",             "image_url": "", "active": True},
        {"id": "kothimbir",   "name": "Kothimbir Vadi",    "category": "Snacks",  "price": 90,  "description": "Steamed, healthy and full of flavour",    "image_url": "", "active": True},
        {"id": "modak",       "name": "Modak (2 pcs)",     "category": "Sweets",  "price": 80,  "description": "Traditional Maharashtrian sweet delight", "image_url": "", "active": True},
        {"id": "kharvas",     "name": "Kharvas",           "category": "Sweets",  "price": 70,  "description": "Slow-set creamy delicacy",                "image_url": "", "active": True},
        {"id": "solkadhi",    "name": "Solkadhi",          "category": "Drinks",  "price": 55,  "description": "Refreshing kokum coconut cooler",         "image_url": "", "active": True},
    ],
    "franchise_fee_inr": 200000,
    "security_deposit_inr": 50000,
    "deposit_refundable": True,
    "deposit_note": "Security deposit is refundable at end of agreement (subject to terms).",
    "setup_heads": [
        {"id": "interiors",  "label": "Interiors & Civil Work",   "amount": 300000, "remarks": ""},
        {"id": "equipment",  "label": "Equipment & Appliances",   "amount": 200000, "remarks": ""},
        {"id": "furniture",  "label": "Furniture & Fixtures",     "amount": 100000, "remarks": ""},
        {"id": "branding",   "label": "Branding & Signage",       "amount": 50000,  "remarks": ""},
        {"id": "stock",      "label": "Initial Stock",            "amount": 50000,  "remarks": ""},
        {"id": "working",    "label": "Working Capital",          "amount": 100000, "remarks": ""},
    ],
    "royalty_pct": 8.0,
    "royalty_gst_applicable": True,
    "marketing_pct": 2.0,
    "royalty_frequency": "monthly",
    "projections": {
        "avg_monthly_sale": 400000,
        "avg_gross_profit": 160000,
        "gross_margin_pct": 40,
        "net_profit_min": 80000,
        "net_profit_max": 110000,
        "breakeven_months": "12-15",
        "roi_months": "18-24",
        "food_cost_pct": 30,
        "packaging_cost_pct": 3,
        "employee_cost_pct": 10,
        "rent_utilities_pct": 8,
        "other_expenses_pct": 3,
    },
    "ideal_locations": [
        "IT Parks", "Corporate Offices", "Malls", "Hospitals",
        "Commercial Complexes", "Colleges", "Universities",
        "Residential Communities", "Airports",
    ],
    "vendors": [
        "Interior Vendor", "Branding Vendor", "Furniture Vendor",
        "Kitchen Equipment Vendor", "Display Counter Vendor",
        "Packaging Vendor", "Lighting Vendor", "Signage Vendor",
    ],
    "footer": {
        "phone": "9741399190",
        "email": "franchise@purnabramha.com",
        "website": "www.purnabramha.com",
    },
    "sections_visible": {
        "menu": True, "model": True, "vendors": True,
        "investment": True, "royalty": True, "projections": True,
        "locations": True, "journey": True, "application": True,
    },
}


@api_router.get("/pb-chai/config")
async def get_pbchai_config():
    """Public: returns the current PB Chai Café config (menu, fees, etc.)."""
    doc = await db.pbchai_config.find_one({"_id_key": "global"}, {"_id": 0})
    if not doc:
        # Seed default
        await db.pbchai_config.insert_one({**DEFAULT_PBCHAI_CONFIG})
        doc = {**DEFAULT_PBCHAI_CONFIG}
    # Merge with defaults so newly-added keys appear even on old docs
    merged = {**DEFAULT_PBCHAI_CONFIG, **doc}
    merged.pop("_id_key", None)
    return merged


@api_router.put("/admin/pb-chai/config")
async def update_pbchai_config(request: Request, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    # Normalise any Google Drive image URLs the admin pastes
    for key in ("logo_url", "kiosk_image_url", "brochure_url"):
        if key in body and body[key]:
            body[key] = _normalize_image_url(body[key])
    for item in body.get("menu_items") or []:
        if item.get("image_url"):
            item["image_url"] = _normalize_image_url(item["image_url"])

    body["_id_key"] = "global"
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    body["updated_by"] = current_user.get("email", "")
    await db.pbchai_config.update_one({"_id_key": "global"}, {"$set": body}, upsert=True)
    doc = await db.pbchai_config.find_one({"_id_key": "global"}, {"_id": 0})
    doc.pop("_id_key", None)
    return doc


@api_router.post("/pb-chai/franchise-application")
async def submit_franchise_app(request: Request):
    body = await request.json()
    name = (body.get("full_name") or "").strip()
    mobile = (body.get("mobile") or "").strip()
    if not name or not mobile:
        raise HTTPException(status_code=400, detail="Name and mobile required")
    doc = {
        "id": str(uuid.uuid4()),
        "full_name": name,
        "mobile": mobile,
        "email": (body.get("email") or "").strip(),
        "city": (body.get("city") or "").strip(),
        "state": (body.get("state") or "").strip(),
        "country": (body.get("country") or "India").strip(),
        "occupation": (body.get("occupation") or "").strip(),
        "business_experience": (body.get("business_experience") or "").strip(),
        "investment_capacity": (body.get("investment_capacity") or "").strip(),
        "preferred_location": (body.get("preferred_location") or "").strip(),
        "available_area": (body.get("available_area") or "").strip(),
        "expected_launch": (body.get("expected_launch") or "").strip(),
        "message": (body.get("message") or "").strip(),
        "agreed_disclosure": bool(body.get("agreed_disclosure", False)),
        "status": "submitted",  # submitted | discussion | approved | fee_paid | agreement | training | launched | rejected
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.pbchai_applications.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.get("/admin/pb-chai/franchise-applications")
async def list_franchise_apps(current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    docs = await db.pbchai_applications.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"applications": docs}


@api_router.patch("/admin/pb-chai/franchise-applications/{app_id}")
async def update_franchise_app(app_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"email": current_user.get("email")}, {"_id": 0})
    if not user_doc or not (user_doc.get("is_admin") or user_doc.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    body = await request.json()
    update = {}
    if "status" in body:
        update["status"] = body["status"]
    if "notes" in body:
        update["notes"] = body["notes"]
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.pbchai_applications.update_one({"id": app_id}, {"$set": update})
    return await db.pbchai_applications.find_one({"id": app_id}, {"_id": 0})







app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["https://www.purnabramha.com", "https://purnabramha.com", "https://purnabramha-app.emergent.host", "https://golden-luxury-app.preview.emergentagent.com", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def seed_admin_account():
    """Ensure admin accounts and book content exist on every startup."""
    # Seed PBadmin account
    existing = await db.users.find_one({"email": "PBadmin@purnabramha.com"}, {"_id": 0})
    if not existing:
        admin_user = {
            "id": str(uuid.uuid4()),
            "email": "PBadmin@purnabramha.com",
            "name": "Admin",
            "phone": "9741399190",
            "password_hash": hash_password("PB22052012"),
            "is_admin": True,
            "created_at": "2025-01-01T00:00:00Z"
        }
        await db.users.insert_one(admin_user)
        logger.info("PBadmin account seeded")

    # Grant admin privileges to owner's Google account
    owner_account = await db.users.find_one({"email": "jayanti.kathale@purnabramha.com"}, {"_id": 0})
    if owner_account:
        await db.users.update_one(
            {"email": "jayanti.kathale@purnabramha.com"},
            {"$set": {"is_admin": True}}
        )
        # Grant book access to all 3 parts
        for part in [1, 2, 3]:
            existing_purchase = await db.book_purchases.find_one(
                {"user_id": owner_account["id"], "part_number": part, "status": "completed"},
                {"_id": 0}
            )
            if not existing_purchase:
                await db.book_purchases.insert_one({
                    "user_id": owner_account["id"],
                    "part_number": part,
                    "session_id": f"owner-grant-{part}",
                    "status": "completed",
                    "purchased_at": datetime.now(timezone.utc).isoformat()
                })
        logger.info("Owner account (jayanti.kathale) granted admin + book access")

    # Seed book pages if not already loaded
    page_count = await db.book_pages.count_documents({})
    if page_count < 152:
        seed_file = ROOT_DIR / 'book_seed_data.json'
        if seed_file.exists():
            with open(seed_file, 'r') as f:
                pages = json.load(f)
            for page in pages:
                await db.book_pages.update_one(
                    {"page_number": page["page_number"]},
                    {"$set": {
                        "page_number": page["page_number"],
                        "part_number": page["part_number"],
                        "content": page["content"],
                        "image_url": None,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }},
                    upsert=True
                )
            logger.info(f"Seeded {len(pages)} book pages")
        else:
            logger.warning("book_seed_data.json not found, skipping book seed")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()