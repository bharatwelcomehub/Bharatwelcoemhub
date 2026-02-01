from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Get Emergent LLM Key
LLM_API_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")


# ===== MODELS =====
class BhojanGuruRequest(BaseModel):
    mode: str  # 'region' or 'body'
    region: Optional[str] = None
    questions: Optional[dict] = None  # For body need mode

class BhojanGuruResponse(BaseModel):
    recommendations: List[str]
    explanation: str

class WishGeneratorRequest(BaseModel):
    center: str
    event_type: str
    names: str
    age_or_year: Optional[str] = None
    from_name: str
    note: Optional[str] = None

class WishGeneratorResponse(BaseModel):
    wish_text: str
    wish_marathi: str

class GuestResponseRequest(BaseModel):
    guest_message: str
    center: str

class GuestResponseResponse(BaseModel):
    reply: str


# ===== AI ENDPOINTS =====
@api_router.post("/ai/bhojan-guru", response_model=BhojanGuruResponse)
async def bhojan_guru(request: BhojanGuruRequest):
    try:
        chat = LlmChat(
            api_key=LLM_API_KEY,
            session_id=f"bhojan-guru-{uuid.uuid4()}",
            system_message="You are Bhojan Guru, an expert in Maharashtrian cuisine. Recommend authentic dishes from Purnabramha restaurant menu based on user preferences."
        ).with_model("openai", "gpt-5.2")
        
        if request.mode == 'region':
            prompt = f"Suggest a complete traditional Maharashtrian thali for {request.region} region. Include specific dishes from categories: Snacks, Main Course (Bhaji), Dal/Varan, Rice, Roti, Sweet, and Drinks. List 8-10 items."
        else:
            prompt = f"Based on these body needs: {request.questions}, suggest a balanced Maharashtrian thali. Consider nutritional requirements and list 8-10 specific dishes."
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse response
        lines = response.strip().split('\n')
        recommendations = [line.strip('- •*').strip() for line in lines if line.strip()]
        
        return BhojanGuruResponse(
            recommendations=recommendations[:10],
            explanation="Personalized thali recommendation based on your preferences"
        )
    except Exception as e:
        logger.error(f"Bhojan Guru error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/wish-generator", response_model=WishGeneratorResponse)
async def wish_generator(request: WishGeneratorRequest):
    try:
        chat = LlmChat(
            api_key=LLM_API_KEY,
            session_id=f"wish-gen-{uuid.uuid4()}",
            system_message="You are a Marathi wish generator. Create beautiful, heartfelt wishes in both English and Marathi for celebrations."
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""Create a celebration wish for:
Event: {request.event_type}
For: {request.names}
Age/Year: {request.age_or_year or 'N/A'}
From: {request.from_name}
Note: {request.note or 'N/A'}
Location: Purnabramha {request.center}

Provide:
1. English wish (2-3 lines)
2. Marathi wish (2-3 lines)
Make it warm and traditional."""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Split English and Marathi
        parts = response.split('\n\n')
        english = parts[0] if len(parts) > 0 else response
        marathi = parts[1] if len(parts) > 1 else "शुभेच्छा!"
        
        return WishGeneratorResponse(
            wish_text=english.strip(),
            wish_marathi=marathi.strip()
        )
    except Exception as e:
        logger.error(f"Wish generator error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/guest-response", response_model=GuestResponseResponse)
async def guest_response(request: GuestResponseRequest):
    try:
        chat = LlmChat(
            api_key=LLM_API_KEY,
            session_id=f"guest-resp-{uuid.uuid4()}",
            system_message="You are a customer service assistant for Purnabramha restaurant. Respond professionally and warmly to customer inquiries."
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""Guest message: {request.guest_message}

Respond as Purnabramha {request.center} staff. Address:
- Booking inquiries
- Menu questions
- Operating hours
- General info
Keep it concise (2-3 sentences). Be warm and helpful."""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        return GuestResponseResponse(reply=response.strip())
    except Exception as e:
        logger.error(f"Guest response error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== BASIC ENDPOINTS =====
@api_router.get("/")
async def root():
    return {"message": "Purnabramha API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "ai_enabled": bool(LLM_API_KEY)}


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
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
