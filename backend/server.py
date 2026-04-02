from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Response, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()