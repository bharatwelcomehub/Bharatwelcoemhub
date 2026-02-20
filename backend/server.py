from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import razorpay
import stripe

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

JWT_SECRET = os.environ.get('JWT_SECRET', 'purnabramha-secret-key-2025')
JWT_ALGORITHM = 'HS256'

razorpay_client = razorpay.Client(auth=(os.environ.get('RAZORPAY_KEY_ID', ''), os.environ.get('RAZORPAY_KEY_SECRET', '')))
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

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
    address: str
    phone: str
    whatsapp: str
    is_active: bool = True

class MenuItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str
    price: float
    image_url: Optional[str] = None
    is_veg: bool = True
    is_available: bool = True

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

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: dict = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**user_doc)

@api_router.get("/locations", response_model=List[Location])
async def get_locations():
    locations = await db.locations.find({"is_active": True}, {"_id": 0}).to_list(100)
    return [Location(**loc) for loc in locations]

@api_router.get("/menu", response_model=List[MenuItem])
async def get_menu(category: Optional[str] = None):
    query = {"is_available": True}
    if category:
        query["category"] = category
    
    items = await db.menu_items.find(query, {"_id": 0}).to_list(1000)
    return [MenuItem(**item) for item in items]

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
        is_available=item_data.get('is_available', True)
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
        "is_available": item_data.get('is_available', True)
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

@api_router.post("/payment/create-razorpay-order")
async def create_razorpay_order(amount: int):
    try:
        order = razorpay_client.order.create({
            "amount": amount * 100,
            "currency": "INR",
            "payment_capture": 1
        })
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/payment/create-stripe-intent")
async def create_stripe_intent(amount: int):
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount * 100,
            currency="usd"
        )
        return {"client_secret": intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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