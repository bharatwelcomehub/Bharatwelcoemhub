import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

locations = [
    {
        "id": "loc-bangalore-hsr",
        "name": "HSR Layout",
        "city": "Bangalore",
        "country": "India",
        "address": "HSR Layout, Bangalore, Karnataka",
        "phone": "+91 8550078515",
        "whatsapp": "+918550078515",
        "google_review_link": "https://g.page/r/purnabramha-hsr/review",
        "is_active": True
    },
    {
        "id": "loc-pune-kharadi",
        "name": "Nyati Mall Kharadi",
        "city": "Pune",
        "country": "India",
        "address": "Nyati Mall, Kharadi, Pune, Maharashtra",
        "phone": "+91 9900089803",
        "whatsapp": "+919900089803",
        "google_review_link": "https://g.page/r/purnabramha-kharadi/review",
        "is_active": True
    },
    {
        "id": "loc-pune-hinjawadi",
        "name": "Hinjawadi",
        "city": "Pune",
        "country": "India",
        "address": "Hinjawadi, Pune, Maharashtra",
        "phone": "+91 9606455434",
        "whatsapp": "+919606455434",
        "google_review_link": "https://g.page/r/purnabramha-hinjawadi/review",
        "is_active": True
    },
    {
        "id": "loc-thane",
        "name": "Thane",
        "city": "Thane",
        "country": "India",
        "address": "Thane, Maharashtra",
        "phone": "+91 8904749084",
        "whatsapp": "+918904749084",
        "google_review_link": "https://g.page/r/purnabramha-thane/review",
        "is_active": True
    },
    {
        "id": "loc-dombivli",
        "name": "Dombivli",
        "city": "Dombivli",
        "country": "India",
        "address": "Dombivli, Maharashtra",
        "phone": "+91 9606455433",
        "whatsapp": "+919606455433",
        "google_review_link": "https://g.page/r/purnabramha-dombivli/review",
        "is_active": True
    },
    {
        "id": "loc-kalyan",
        "name": "Kalyan",
        "city": "Kalyan",
        "country": "India",
        "address": "Kalyan, Maharashtra",
        "phone": "+91 8792887442",
        "whatsapp": "+918792887442",
        "google_review_link": "https://g.page/r/purnabramha-kalyan/review",
        "is_active": True
    },
    {
        "id": "loc-sambhaji-nagar",
        "name": "Sambhaji Nagar",
        "city": "Sambhaji Nagar",
        "country": "India",
        "address": "Sambhaji Nagar, Maharashtra",
        "phone": "+91 8971049084",
        "whatsapp": "+918971049084",
        "google_review_link": "https://g.page/r/purnabramha-sambhajinagar/review",
        "is_active": True
    },
    {
        "id": "loc-perth",
        "name": "Perth",
        "city": "Perth",
        "country": "Australia",
        "address": "Perth, Western Australia",
        "phone": "+61 401832922",
        "whatsapp": "+61401832922",
        "google_review_link": "https://g.page/r/purnabramha-perth/review",
        "is_active": True
    }
]

menu_items = [
    {
        "id": "item-misal-pav",
        "name": "Misal Pav",
        "description": "Spicy sprouted lentil curry topped with farsan, onions, lemon, and served with pav",
        "category": "Breakfast",
        "price": 120.0,
        "image_url": "https://images.pexels.com/photos/30769679/pexels-photo-30769679.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=350&w=500",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-vada-pav",
        "name": "Vada Pav",
        "description": "Mumbai's iconic street food - spiced potato fritter in a bun with chutneys",
        "category": "Snacks",
        "price": 40.0,
        "image_url": "https://images.pexels.com/photos/17433352/pexels-photo-17433352.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=350&w=500",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-poha",
        "name": "Poha",
        "description": "Flattened rice cooked with onions, potatoes, peanuts, and aromatic spices",
        "category": "Breakfast",
        "price": 80.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-pav-bhaji",
        "name": "Pav Bhaji",
        "description": "Spicy mixed vegetable curry served with buttered pav bread",
        "category": "Main Course",
        "price": 150.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-puran-poli",
        "name": "Puran Poli",
        "description": "Sweet flatbread stuffed with jaggery and lentil filling",
        "category": "Desserts",
        "price": 100.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-thali",
        "name": "Maharashtrian Thali",
        "description": "Complete meal with bhakri, bhaji, dal, rice, amti, and sweet",
        "category": "Thali",
        "price": 250.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-sabudana-khichdi",
        "name": "Sabudana Khichdi",
        "description": "Tapioca pearls cooked with peanuts, potatoes, and mild spices",
        "category": "Breakfast",
        "price": 90.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-batata-vada",
        "name": "Batata Vada",
        "description": "Crispy potato fritters with garlic chutney",
        "category": "Snacks",
        "price": 60.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-thalipeeth",
        "name": "Thalipeeth",
        "description": "Multi-grain flatbread with spices, served with yogurt and pickle",
        "category": "Breakfast",
        "price": 100.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-kanda-bhaji",
        "name": "Kanda Bhaji",
        "description": "Crispy onion fritters, perfect with hot chai",
        "category": "Snacks",
        "price": 70.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-sol-kadhi",
        "name": "Sol Kadhi",
        "description": "Refreshing coconut milk drink with kokum",
        "category": "Beverages",
        "price": 50.0,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "item-masala-chai",
        "name": "Masala Chai",
        "description": "Traditional spiced tea",
        "category": "Beverages",
        "price": 30.0,
        "is_veg": True,
        "is_available": True
    }
]

async def seed_database():
    print("Seeding database...")
    
    await db.locations.delete_many({})
    await db.locations.insert_many(locations)
    print(f"Inserted {len(locations)} locations")
    
    await db.menu_items.delete_many({})
    await db.menu_items.insert_many(menu_items)
    print(f"Inserted {len(menu_items)} menu items")
    
    print("Database seeded successfully!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
