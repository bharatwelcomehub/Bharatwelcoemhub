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
    {
        "id": "pudachi-vadi",
        "name": "Pudachi Vadi",
        "description": "Deep-fried gram flour rolls with coconut. Best with: Solkadhi",
        "category": "Snacks",
        "price": 180.0,
        "price_inr": 180.0,
        "price_aud": 17.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "dadpe-pohe",
        "name": "Dadpe Pohe",
        "description": "Cold poha mixed with coconut and curd. Best with: Buttermilk",
        "category": "Snacks",
        "price": 120.0,
        "price_inr": 120.0,
        "price_aud": 11.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "snacks-platter",
        "name": "Snacks Platter",
        "description": "Assorted snack platter for sharing. Best with: Masala Tea",
        "category": "Snacks",
        "price": 430.0,
        "price_inr": 430.0,
        "price_aud": 42.99,
        "is_veg": True,
        "is_available": True
    },
    
    # Heavy Brunch
    {
        "id": "misal-pav",
        "name": "Misal Pav",
        "description": "Spicy Nashik-style misal topped with farsan. Best with: Solkadhi",
        "category": "Heavy Brunch",
        "price": 150.0,
        "price_inr": 150.0,
        "price_aud": 14.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/misal%20pav.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "thalipith",
        "name": "Thalipith",
        "description": "Mixed-grain savoury Maharashtrian pancake. Best with: Buttermilk",
        "category": "Heavy Brunch",
        "price": 140.0,
        "price_inr": 140.0,
        "price_aud": 13.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "shrikhanda-puri-bhaji",
        "name": "Shrikhanda Puri Bhaji",
        "description": "Sweet shrikhanda with puri and potato bhaji. Best with: Masala Coffee",
        "category": "Heavy Brunch",
        "price": 180.0,
        "price_inr": 180.0,
        "price_aud": 17.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "aloocha-paratha",
        "name": "Aloocha Paratha",
        "description": "Potato-stuffed paratha served hot. Best with: Buttermilk",
        "category": "Heavy Brunch",
        "price": 80.0,
        "price_inr": 80.0,
        "price_aud": 7.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "puri-bhaji",
        "name": "Puri Bhaji",
        "description": "Classic puri served with potato bhaji. Best with: Masala Tea",
        "category": "Heavy Brunch",
        "price": 140.0,
        "price_inr": 140.0,
        "price_aud": 13.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "ghavan",
        "name": "Ghavan",
        "description": "Thin rice flour pancakes from Konkan. Best with: Buttermilk",
        "category": "Heavy Brunch",
        "price": 130.0,
        "price_inr": 130.0,
        "price_aud": 12.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "varan-fal",
        "name": "Varan Fal",
        "description": "Soft dough dumplings cooked in lentil curry. Best with: Buttermilk",
        "category": "Heavy Brunch",
        "price": 210.0,
        "price_inr": 210.0,
        "price_aud": 20.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "shengole",
        "name": "Shengole",
        "description": "Traditional spicy Maharashtrian pasta dish. Best with: Buttermilk",
        "category": "Heavy Brunch",
        "price": 210.0,
        "price_inr": 210.0,
        "price_aud": 20.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Slide20.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    
    # Rice
    {
        "id": "sadha-bhat",
        "name": "Sadha Bhat",
        "description": "Steamed plain rice cooked to perfection. Best with: Dal",
        "category": "Rice",
        "price": 145.0,
        "price_inr": 145.0,
        "price_aud": 14.47,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_steamed%20rice.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kande-bhat",
        "name": "Kande Bhat",
        "description": "Rice cooked with onions, turmeric, and mild spices. Best with: Dal",
        "category": "Rice",
        "price": 160.0,
        "price_inr": 160.0,
        "price_aud": 15.93,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "dahi-bhat",
        "name": "Dahi Bhat",
        "description": "Curd rice tempered with mustard seeds and curry leaves. Best with: Buttermilk",
        "category": "Rice",
        "price": 160.0,
        "price_inr": 160.0,
        "price_aud": 15.93,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Slide8.JPG/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "masale-bhat",
        "name": "Masale Bhat",
        "description": "Spiced rice cooked with vegetables and Maharashtrian masala. Best with: Raita",
        "category": "Rice",
        "price": 218.0,
        "price_inr": 218.0,
        "price_aud": 21.75,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "gola-bhat",
        "name": "Gola Bhat",
        "description": "Rice served with gram flour dumplings in spicy sauce. Best with: Buttermilk",
        "category": "Rice",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/PhotoRoom-20231116_221119.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "ravan-bhat",
        "name": "Ravan Bhat",
        "description": "Spicy and tangy rice with bold flavours. Best with: Buttermilk",
        "category": "Rice",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Slide2.JPG/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "tup-bhat",
        "name": "Tup Bhat",
        "description": "Fragrant ghee rice with spices and dry fruits. Best with: Kadhi",
        "category": "Rice",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_tup%20bhat.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    
    # Dal
    {
        "id": "sadha-varan",
        "name": "Sadha Varan",
        "description": "Plain yellow lentil curry with mild tempering. Best with: Rice",
        "category": "Dal",
        "price": 145.0,
        "price_inr": 145.0,
        "price_aud": 14.47,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Slide8-0003.JPG/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kadhi",
        "name": "Kadhi",
        "description": "Tangy yoghurt-based curry thickened with gram flour. Best with: Rice",
        "category": "Dal",
        "price": 145.0,
        "price_inr": 145.0,
        "price_aud": 14.47,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "lasun-varan",
        "name": "Lasun Varan",
        "description": "Garlic-flavoured lentil curry with green chillies. Best with: Rice",
        "category": "Dal",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "pandhara-rassa",
        "name": "Pandhara Rassa",
        "description": "White coconut-based curry with mild spice. Best with: Rice",
        "category": "Dal",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "fodnich-varan",
        "name": "Fodnich Varan",
        "description": "Tempered tur dal with garlic and spices. Best with: Rice",
        "category": "Dal",
        "price": 210.0,
        "price_inr": 210.0,
        "price_aud": 21.02,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_vodnich%20varan.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "mataki-amti",
        "name": "Mataki Amti",
        "description": "Spicy sprouted lentil curry rich in protein. Best with: Rice",
        "category": "Dal",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "is_veg": True,
        "is_available": True
    },
    
    # Bhaji
    {
        "id": "jeera-aloo",
        "name": "Jeera Aloo",
        "description": "Potatoes tossed with cumin seeds and mild spices. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "aloo-dry",
        "name": "Aloo Dry",
        "description": "Dry spiced potato curry prepared without onion or garlic. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 181.0,
        "price_inr": 181.0,
        "price_aud": 18.11,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_aloo%20bhaji.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "dry-zhunka",
        "name": "Dry Zhunka",
        "description": "Spiced gram flour stir-fry with onions — rustic Maharashtrian classic. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 210.0,
        "price_inr": 210.0,
        "price_aud": 21.02,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/fb_2841145152681673_1280x720-0001.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "pithala",
        "name": "Pithala",
        "description": "Thick gram flour curry, mildly spiced and comforting. Best with: Buttermilk & Bhakar",
        "category": "Bhaji",
        "price": 276.0,
        "price_inr": 276.0,
        "price_aud": 27.56,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "bharali-vangi",
        "name": "Bharali Vangi",
        "description": "Stuffed baby eggplants cooked in spiced coconut gravy. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 254.0,
        "price_inr": 254.0,
        "price_aud": 25.38,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_brinjal.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "mataki-usal",
        "name": "Mataki Usal",
        "description": "Sprouted lentils cooked in spicy onion-tomato gravy. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 218.0,
        "price_inr": 218.0,
        "price_aud": 21.75,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "shev-bhaji",
        "name": "Shev Bhaji",
        "description": "Crunchy chickpea noodles cooked in rich spicy gravy. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 276.0,
        "price_inr": 276.0,
        "price_aud": 27.56,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_shevbhaji.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "bharit",
        "name": "Bharit",
        "description": "Roasted eggplant mash with garlic and spices. Best with: Buttermilk",
        "category": "Bhaji",
        "price": 276.0,
        "price_inr": 276.0,
        "price_aud": 27.56,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_baigan%20bharta.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kaju-curry",
        "name": "Kaju Curry",
        "description": "Creamy cashew nut curry with mild sweetness. Best with: Masala Chai",
        "category": "Bhaji",
        "price": 348.0,
        "price_inr": 348.0,
        "price_aud": 34.84,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/IMG_20200503_120338.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    
    # Roti
    {
        "id": "bhakar",
        "name": "Bhakar",
        "description": "Classic bhakar served hot",
        "category": "Roti",
        "price": 25.0,
        "price_inr": 25.0,
        "price_aud": 2.49,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "dupodi-poli",
        "name": "Dupodi Poli",
        "description": "Soft dupodi poli, freshly made",
        "category": "Roti",
        "price": 15.0,
        "price_inr": 15.0,
        "price_aud": 1.49,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "puri-set",
        "name": "Puri Set (5pc)",
        "description": "Crisp puris (5 pieces)",
        "category": "Roti",
        "price": 50.0,
        "price_inr": 50.0,
        "price_aud": 4.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "rice-bhakar",
        "name": "Rice Bhakar",
        "description": "Rice bhakar served hot",
        "category": "Roti",
        "price": 25.0,
        "price_inr": 25.0,
        "price_aud": 2.49,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "pav-1pc",
        "name": "Pav 1pc",
        "description": "Single pav bun",
        "category": "Roti",
        "price": 10.0,
        "price_inr": 10.0,
        "price_aud": 0.99,
        "is_veg": True,
        "is_available": True
    },
    
    # Sweets
    {
        "id": "shrikhanda",
        "name": "Shrikhanda",
        "description": "Sweetened hung curd flavoured with saffron. Best with: Masala Coffee",
        "category": "Sweets",
        "price": 150.0,
        "price_inr": 150.0,
        "price_aud": 14.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Rodaga%20SM%20Monday%2007.jpg/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "puranpoli",
        "name": "Puranpoli",
        "description": "Sweet lentil-stuffed flatbread. Best with: Milk",
        "category": "Sweets",
        "price": 100.0,
        "price_inr": 100.0,
        "price_aud": 9.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/Purnabramha_puranpoli.png/:/rs=h:350,m",
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "basundi",
        "name": "Basundi",
        "description": "Slow-reduced milk dessert with cardamom. Best with: Masala Coffee",
        "category": "Sweets",
        "price": 150.0,
        "price_inr": 150.0,
        "price_aud": 14.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "modak",
        "name": "Modak",
        "description": "Steamed rice dumplings with coconut-jaggery filling. Best with: Masala Coffee",
        "category": "Sweets",
        "price": 190.0,
        "price_inr": 190.0,
        "price_aud": 18.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "khova-poli",
        "name": "Khova Poli",
        "description": "Milk-solid stuffed festive sweet. Best with: Milk",
        "category": "Sweets",
        "price": 100.0,
        "price_inr": 100.0,
        "price_aud": 9.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "sheera",
        "name": "Sheera",
        "description": "Classic semolina dessert with ghee. Best with: Masala Coffee",
        "category": "Sweets",
        "price": 150.0,
        "price_inr": 150.0,
        "price_aud": 14.99,
        "is_veg": True,
        "is_available": True
    },
    {
        "id": "kharvas",
        "name": "Kharvas",
        "description": "Traditional milk pudding. Best with: Milk",
        "category": "Sweets",
        "price": 300.0,
        "price_inr": 300.0,
        "price_aud": 29.99,
        "image_url": "https://img1.wsimg.com/isteam/ip/d44003e6-5826-4a6c-9570-8bdf48c3c47a/IMG_20200603_121003.jpg/:/rs=h:350,m",
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
