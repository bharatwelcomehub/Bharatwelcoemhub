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
    wish_image_url: Optional[str] = None

class GuestResponseRequest(BaseModel):
    guest_message: str
    center: str

class GuestResponseResponse(BaseModel):
    reply: str


# ===== AI ENDPOINTS =====
@api_router.post("/ai/bhojan-guru", response_model=BhojanGuruResponse)
async def bhojan_guru(request: BhojanGuruRequest):
    try:
        # Menu items to suggest from
        menu_items = """
        Snacks: Kanda Bhaji, Maaswadi, Sabudana Vada, Batate Vada, Kachori, Vada Pav, Kanda Pohe, Tarri Pohe, Dadpe Pohe, Alu Vadi, Kothimbir Vadi, Mataki Bhel
        Heavy Brunch: Thalipith, Ghavan, Dhirde, Misal Pav, Puri Bhaji, Shrikhand Puri Bhaji, Varan Fal, Shengole
        Main Course: Ravan Pithala, Pithala, Bharit, Dal Vanga, Mix Cauliflower Bhaji, Shev Bhaji, Patodi Rassa, Maaswadi Rassa, Bharli Vangi, Zhunka, Kaju Curry, Akkha Masur, Kadhi Gole, Jeera Aloo, Matki Usal
        Dal: Mataki Amti, Lasun Varan, Sadha Varan, Takachi Kadhi, Kataachi Amti, Jeera Varan, Chef Special Dal
        Rice: Steam Rice, Dahi Bhat, Kanda Rice, Tup Bhat, Bhaji Bhat, Gola Bhat, Ravan Bhat, Masale Bhat, Tup Varan Bhat, Khajur Bhat
        Desserts: Modak, Shrikhanda, Shirvale, Puranpoli, Khava Poli, Tilgul Poli, Kharvas, Amrakhanda, Sheera, Basundi, Shewaya Kheer, Aamras, Chirote, Mungdal Halwa, Gulshela, Gajar Halwa, Gulabjam
        Drinks: Simple Tea, Masala Tea, Ginger Tea, Black Tea, Coffee, Solkadhi, Piyush, Kokum, Buttermilk, Lime Juice
        Kids Menu: BG Shrikhanda Puri Bhaji, BG Misal Pav, BG Khichadi, BG Sabudana Khichadi, BG Aloocha Paratha, BG Vada Pav, BG Puranpoli, BG Shrikhanda
        """
        
        chat = LlmChat(
            api_key=LLM_API_KEY,
            session_id=f"bhojan-guru-{uuid.uuid4()}",
            system_message=f"You are Bhojan Guru, expert in Maharashtrian cuisine at Purnabramha. Recommend ONLY from this menu:\n{menu_items}"
        ).with_model("openai", "gpt-5.2")
        
        if request.mode == 'region':
            prompt = f"Suggest a complete traditional Maharashtrian thali for {request.region} region. Use ONLY items from the menu provided. List 8-10 specific items."
        else:
            # Body need mode with 6 questions
            answers = request.questions or {}
            prompt = f"""Based on these health/mood indicators:
1. Energy Level: {answers.get('energy', 'Normal')}
2. Appetite: {answers.get('appetite', 'Normal')}
3. Digestive State: {answers.get('digestion', 'Good')}
4. Mood: {answers.get('mood', 'Neutral')}
5. Activity Level: {answers.get('activity', 'Moderate')}
6. Special Needs: {answers.get('special', 'None')}

Suggest a balanced thali from the menu that suits their body needs. List 8-10 specific items ONLY from the provided menu."""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse response
        lines = response.strip().split('\n')
        recommendations = [line.strip('- •*123456789.').strip() for line in lines if line.strip() and any(c.isalpha() for c in line)]
        
        return BhojanGuruResponse(
            recommendations=recommendations[:10],
            explanation="Personalized thali recommendation from Purnabramha menu"
        )
    except Exception as e:
        logger.error(f"Bhojan Guru error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/wish-generator", response_model=WishGeneratorResponse)
async def wish_generator(request: WishGeneratorRequest):
    try:
        # Generate text wish
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
        
        # For now, return without image as emergentintegrations.llm.image doesn't exist
        # Image generation can be added later with proper library
        
        return WishGeneratorResponse(
            wish_text=english.strip(),
            wish_marathi=marathi.strip(),
            wish_image_url=None
        )
    except Exception as e:
        logger.error(f"Wish generator error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/guest-response", response_model=GuestResponseResponse)
async def guest_response(request: GuestResponseRequest):
    try:
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        current_day = datetime.now().strftime("%A")
        
        # All Purnabramha Centers Information
        centers_info = """
Purnabramha Centers:
1. Perth, Australia 🇦🇺 - WhatsApp: +61 401 832 922
2. HSR Bangalore, India 🇮🇳 - WhatsApp: +91 85500 78515
3. Thane Mumbai, India 🇮🇳 - WhatsApp: +91 89047 49084
4. Ch. Sambhajinagar, India 🇮🇳 - WhatsApp: +91 89710 49084
5. Dombivli Mumbai, India 🇮🇳 - WhatsApp: +91 96064 55433
6. Kharadi Pune, India 🇮🇳 - WhatsApp: +91 9900089803
7. Hinjawadi Pune, India 🇮🇳 - WhatsApp: +91 9606455434

All centers serve 100% Maharashtrian vegetarian cuisine.
"""
        
        chat = LlmChat(
            api_key=LLM_API_KEY,
            session_id=f"guest-resp-{uuid.uuid4()}",
            system_message=f"""You are a customer service assistant for Purnabramha restaurant chain. 
Today is {current_day}, {current_date}. 
Currently responding from: {request.center} center.

IMPORTANT: Purnabramha has 7 centers (Perth in Australia + 6 in India). ALL are operational.
{centers_info}

When guest asks about ANY center location:
- Confirm the center EXISTS
- Provide the WhatsApp number for that specific center
- Be helpful and accurate

Respond professionally, warmly, and include appropriate emoticons/emojis."""
        ).with_model("openai", "gpt-5.2")
        
        prompt = f"""Guest message: {request.guest_message}

Current Date: {current_day}, {current_date}
You are responding from: {request.center}

Guidelines:
- Location inquiries: Share accurate info about all 7 centers with WhatsApp numbers 📍
- Booking inquiries (use 📅 🍽️): Check if date is in the past and inform accordingly
- Menu questions (use 🍛 🥘)
- Operating hours (use ⏰ 🕐)
- General info (use ℹ️ 👋)
- Greetings (use 🙏 😊)

If guest mentions yesterday, past dates, or any date before today, politely say: "Sorry, we can only accept bookings for future dates 📅. Would you like to book for tomorrow or any upcoming date? 😊"

If guest asks about a specific center (Perth, HSR, Thane, etc.), confirm it exists and share the WhatsApp number.

Keep it concise (2-3 sentences). Be warm, helpful and include relevant emoticons."""
        
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
