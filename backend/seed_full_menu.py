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

# Complete menu with India and Australia pricing
menu_items = [
    # Balgopal (Kids Menu)
    {
        "id": "balgopal-vada-pav",
        "name": "Balgopal Vada Pav",
        "description": "Mini mild vada pav for kids. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 40.0,
        "price_inr": 40.0,
        "price_aud": 3.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-sabudana-vada",
        "name": "Balgopal Sabudana Vada",
        "description": "Soft sabudana vadas for children. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 130.0,
        "price_inr": 130.0,
        "price_aud": 12.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-kanda-pohe",
        "name": "Balgopal Kanda Pohe",
        "description": "Mild poha prepared for kids. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 80.0,
        "price_inr": 80.0,
        "price_aud": 7.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-tedamedha-aloo",
        "name": "Balgopal Tedamedha Aloo",
        "description": "Soft mashed potato dish. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 60.0,
        "price_inr": 60.0,
        "price_aud": 5.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-thali",
        "name": "Balgopal Thali",
        "description": "Balanced kids thali with multiple items. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 300.0,
        "price_inr": 300.0,
        "price_aud": 29.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-varan-fal",
        "name": "Balgopal Varan Fal",
        "description": "Soft dumplings in mild dal. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 140.0,
        "price_inr": 140.0,
        "price_aud": 13.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-tup-varan-bhat",
        "name": "Balgopal Tup Varan Bhat",
        "description": "Dal rice with ghee for kids. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 100.0,
        "price_inr": 100.0,
        "price_aud": 9.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/PhotoRoom-20231117_060441.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-shrikhanda",
        "name": "Balgopal Shrikhanda",
        "description": "Sweet yoghurt dessert for kids. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 100.0,
        "price_inr": 100.0,
        "price_aud": 9.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "balgopal-khova-poli",
        "name": "Balgopal Khova Poli",
        "description": "Milk-solid filled sweet. Best with: Milk",
        "category": "Balgopal (Kids)",
        "price": 110.0,
        "price_inr": 110.0,
        "price_aud": 10.99,
        "is_veg": True,
        "is_available": True
    },
    
    # Drinks
    {
        "id": "masala-lime-juice",
        "name": "Masala Lime Juice",
        "description": "Lime juice with house masala",
        "category": "Drinks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "masala-buttermilk",
        "name": "Masala Buttermilk",
        "description": "Spiced buttermilk with herbs and tempering",
        "category": "Drinks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_masala%20buttermilk%20(1).jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "piyush",
        "name": "Piyush",
        "description": "Sweet yoghurt-based Maharashtrian drink",
        "category": "Drinks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "solkadhi",
        "name": "Solkadhi",
        "description": "Coconut milk and kokum digestive drink",
        "category": "Drinks",
        "price": 150.0,
        "price_inr": 150.0,
        "price_aud": 14.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_sol%20kadhi.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kokum",
        "name": "Kokum",
        "description": "Refreshing kokum drink from Konkan",
        "category": "Drinks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_kokum1.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "masala-kokum",
        "name": "Masala Kokum",
        "description": "Kokum drink with added spice",
        "category": "Drinks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "simple-tea",
        "name": "Simple Tea",
        "description": "Classic Indian tea brewed with milk, warm and comforting",
        "category": "Drinks",
        "price": 40.0,
        "price_inr": 40.0,
        "price_aud": 3.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Slide3-0001.JPG/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "masala-tea",
        "name": "Masala Tea",
        "description": "Traditional spiced chai with ginger and aromatic masala",
        "category": "Drinks",
        "price": 50.0,
        "price_inr": 50.0,
        "price_aud": 4.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "simple-coffee",
        "name": "Simple Coffee",
        "description": "Smooth milk coffee with balanced roast",
        "category": "Drinks",
        "price": 50.0,
        "price_inr": 50.0,
        "price_aud": 4.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "masala-coffee",
        "name": "Masala Coffee",
        "description": "Coffee infused with nutmeg and cardamom",
        "category": "Drinks",
        "price": 60.0,
        "price_inr": 60.0,
        "price_aud": 5.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "lime-juice",
        "name": "Lime Juice",
        "description": "Fresh lime juice with sugar and salt",
        "category": "Drinks",
        "price": 70.0,
        "price_inr": 70.0,
        "price_aud": 6.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_masala%20lime%20(1).jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "buttermilk",
        "name": "Buttermilk",
        "description": "Cooling curd-based drink, great for digestion",
        "category": "Drinks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "ginger-tea",
        "name": "Ginger Tea",
        "description": "Strong ginger-infused tea with a bold finish",
        "category": "Drinks",
        "price": 50.0,
        "price_inr": 50.0,
        "price_aud": 4.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "black-tea",
        "name": "Black Tea",
        "description": "Plain black tea, light and refreshing",
        "category": "Drinks",
        "price": 40.0,
        "price_inr": 40.0,
        "price_aud": 3.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "black-coffee",
        "name": "Black Coffee",
        "description": "Strong black coffee with deep roasted flavours",
        "category": "Drinks",
        "price": 50.0,
        "price_inr": 50.0,
        "price_aud": 4.99,
        "is_veg": True,
        "is_available": True
    },
    
    # Snacks
    {
        "id": "vada-pav",
        "name": "Vada Pav",
        "description": "Mumbai-style vada pav with chutney and green chilli. Best with: Masala Chai",
        "category": "Snacks",
        "price": 50.0,
        "price_inr": 50.0,
        "price_aud": 4.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/1080x1080.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "batata-vada",
        "name": "Batata Vada",
        "description": "Classic potato fritters, crunchy outside. Best with: Masala Chai",
        "category": "Snacks",
        "price": 160.0,
        "price_inr": 160.0,
        "price_aud": 15.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_battate%20vada.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "sabudana-vada",
        "name": "Sabudana Vada",
        "description": "Golden sabudana patties, crispy and soft. Best with: Buttermilk",
        "category": "Snacks",
        "price": 140.0,
        "price_inr": 140.0,
        "price_aud": 13.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_sabudana%20vada.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kothimbir-vadi",
        "name": "Kothimbir Vadi",
        "description": "Steamed coriander fritters lightly pan-fried. Best with: Buttermilk",
        "category": "Snacks",
        "price": 180.0,
        "price_inr": 180.0,
        "price_aud": 17.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_kothimbeer%20vadi.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "alu-vadi",
        "name": "Alu Vadi",
        "description": "Taro leaf rolls cooked with spices. Best with: Solkadhi",
        "category": "Snacks",
        "price": 180.0,
        "price_inr": 180.0,
        "price_aud": 17.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kande-pohe",
        "name": "Kande Pohe",
        "description": "Flattened rice with onion, peanuts and lemon. Best with: Masala Tea",
        "category": "Snacks",
        "price": 140.0,
        "price_inr": 140.0,
        "price_aud": 13.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kachori",
        "name": "Kachori",
        "description": "Flaky kachori stuffed with spiced peas. Best with: Masala Tea",
        "category": "Snacks",
        "price": 170.0,
        "price_inr": 170.0,
        "price_aud": 16.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_kachori%20(2).png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "bread-pakoda",
        "name": "Bread Pakoda",
        "description": "Bread fritters served with chutneys. Best with: Masala Tea",
        "category": "Snacks",
        "price": 90.0,
        "price_inr": 90.0,
        "price_aud": 8.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "masala-bread-pakoda",
        "name": "Masala Bread Pakoda",
        "description": "Bread pakoda stuffed with spiced potato. Best with: Masala Tea",
        "category": "Snacks",
        "price": 110.0,
        "price_inr": 110.0,
        "price_aud": 10.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kanda-bhaji",
        "name": "Kanda Bhaji",
        "description": "Crispy onion fritters served hot. Best with: Masala Chai",
        "category": "Snacks",
        "price": 130.0,
        "price_inr": 130.0,
        "price_aud": 12.99,
        "is_veg": True,
        "is_available": True
    },
]

async def seed_menu():
    print("Clearing existing menu items...")
    await db.menu_items.delete_many({})
    
    print("Inserting new menu items...")
    await db.menu_items.insert_many(menu_items)
    
    print(f"✅ Successfully inserted {len(menu_items)} menu items!")
    print("\nMenu categories loaded:")
    categories = set(item['category'] for item in menu_items)
    for cat in sorted(categories):
        count = sum(1 for item in menu_items if item['category'] == cat)
        print(f"  - {cat}: {count} items")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_menu())
