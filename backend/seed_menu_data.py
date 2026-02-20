"""
Seed script for Purnabramha menu data from official PDF menus
Run: python seed_menu_data.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# Complete menu data extracted from PDFs
MENU_DATA = [
    # BALGOPAL (KIDS) MENU
    {"name": "BG Shrikhanda Puri Bhaji", "description": "Sweet yoghurt dessert served with puris and spiced potato curry - Kids portion", "category": "Balgopal (Kids)", "price_inr": 219, "price_aud": 15.99, "is_veg": True},
    {"name": "BG Misal Pav", "description": "Spicy mixed lentil curry topped with farsan, served with soft bread rolls - Kids portion", "category": "Balgopal (Kids)", "price_inr": 189, "price_aud": 12.99, "is_veg": True},
    {"name": "BG MungDal Khichadi", "description": "Soft, comforting khichadi made with mung dal and ghee - Kids portion", "category": "Balgopal (Kids)", "price_inr": 199, "price_aud": 8.99, "is_veg": True},
    {"name": "BG Sabudana Khichadi", "description": "Tapioca pearls stir-fried with potato, peanuts, and mild spices - Kids portion", "category": "Balgopal (Kids)", "price_inr": 189, "price_aud": 12.99, "is_veg": True},
    {"name": "BG Aloocha Paratha", "description": "Soft flatbread stuffed with seasoned mashed potatoes - Kids portion", "category": "Balgopal (Kids)", "price_inr": 189, "price_aud": 7.99, "is_veg": True},
    {"name": "BG Vada Pav", "description": "Spiced potato fritter served in a soft bun with tangy chutney - Kids portion", "category": "Balgopal (Kids)", "price_inr": 45, "price_aud": 4.99, "is_veg": True},
    {"name": "BG Sabudana Vada (4 pcs)", "description": "Crispy sago and potato patties - crunchy outside, soft inside - Kids portion", "category": "Balgopal (Kids)", "price_inr": 199, "price_aud": 12.99, "is_veg": True},
    {"name": "BG Kanda Pohe", "description": "Flaked rice cooked with onions, peanuts, mustard seeds and curry leaves - Kids portion", "category": "Balgopal (Kids)", "price_inr": 129, "price_aud": 7.99, "is_veg": True},
    {"name": "BG Tedamedha Aloo", "description": "Spiced potato preparation for kids", "category": "Balgopal (Kids)", "price_inr": 129, "price_aud": 5.99, "is_veg": True},
    {"name": "Balgopal Thali", "description": "Complete kids thali with variety of items", "category": "Balgopal (Kids)", "price_inr": 399, "price_aud": None, "is_veg": True},
    {"name": "Balgopal Varan Fal", "description": "Small wheat dumplings cooked in rich yellow lentil curry - Kids portion", "category": "Balgopal (Kids)", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Balgopal Tup Varan Bhat", "description": "Fragrant ghee rice with dal - Kids portion", "category": "Balgopal (Kids)", "price_inr": 149, "price_aud": 9.99, "is_veg": True},
    {"name": "Balgopal Puranpoli", "description": "Sweet lentil-stuffed bread - Kids portion", "category": "Balgopal (Kids)", "price_inr": 149, "price_aud": 9.99, "is_veg": True},
    {"name": "Balgopal Shrikhanda", "description": "Sweet hung curd dessert - Kids portion", "category": "Balgopal (Kids)", "price_inr": 149, "price_aud": 9.99, "is_veg": True},
    {"name": "Balgopal Khova Poli", "description": "Khoya stuffed sweet bread - Kids portion", "category": "Balgopal (Kids)", "price_inr": 149, "price_aud": 10.99, "is_veg": True},

    # TEA / COFFEE
    {"name": "Simple Tea", "description": "Simple tea made with pure cow milk", "category": "Tea & Coffee", "price_inr": 55, "price_aud": None, "is_veg": True},
    {"name": "Masala Tea", "description": "Traditional spiced tea with milk, ginger, and aromatic spices – rich and fragrant", "category": "Tea & Coffee", "price_inr": 65, "price_aud": 4.99, "is_veg": True},
    {"name": "Ginger Tea", "description": "The spicy & kadak chai lovers best choice", "category": "Tea & Coffee", "price_inr": 65, "price_aud": None, "is_veg": True},
    {"name": "Black Tea", "description": "For Black Tea Lovers", "category": "Tea & Coffee", "price_inr": 65, "price_aud": None, "is_veg": True},
    {"name": "Simple Milk Coffee", "description": "Hot coffee made with milk and sugar – smooth and creamy", "category": "Tea & Coffee", "price_inr": 75, "price_aud": 4.99, "is_veg": True},
    {"name": "Black Coffee", "description": "Strong, unsweetened coffee served hot – bold and energising", "category": "Tea & Coffee", "price_inr": 50, "price_aud": 4.99, "is_veg": True},
    {"name": "Masala Coffee", "description": "Specially handcrafted masala for coffee lover with flavours of nutmeg and cardamom", "category": "Tea & Coffee", "price_inr": 95, "price_aud": None, "is_veg": True},

    # NON TEA / DRINKS
    {"name": "Solkadhi", "description": "Traditional Konkan drink made from coconut milk and kokum, lightly spiced – cooling and tangy", "category": "Drinks", "price_inr": 199, "price_aud": 11.99, "is_veg": True},
    {"name": "Piyush", "description": "Sweet, thick beverage made with yoghurt, milk, and saffron – creamy and indulgent", "category": "Drinks", "price_inr": 199, "price_aud": 11.99, "is_veg": True},
    {"name": "Mango Piyush", "description": "Sweet mango flavored yoghurt drink with saffron", "category": "Drinks", "price_inr": 219, "price_aud": 2.99, "is_veg": True},
    {"name": "Kokum", "description": "Kokum the purest form of vitamin C – tangy, healthy, and rejuvenating", "category": "Drinks", "price_inr": 129, "price_aud": 7.99, "is_veg": True},
    {"name": "Masala Kokum", "description": "Spiced kokum drink enriched with house masala – tangy, healthy, and rejuvenating", "category": "Drinks", "price_inr": 149, "price_aud": 8.99, "is_veg": True},
    {"name": "Butter Milk", "description": "Chilled drink made from yoghurt and water, lightly seasoned with spices – cool and digestive", "category": "Drinks", "price_inr": 129, "price_aud": 7.99, "is_veg": True},
    {"name": "Masala Butter Milk", "description": "Spiced version of buttermilk with tadka", "category": "Drinks", "price_inr": 149, "price_aud": 8.99, "is_veg": True},
    {"name": "Lime Juice", "description": "Fresh lime juice balanced with salt, sugar – perfectly refreshing", "category": "Drinks", "price_inr": 129, "price_aud": 6.99, "is_veg": True},
    {"name": "Masala Lime", "description": "Fresh lime juice with Purnabramha's signature spice mix – perfectly refreshing with tangy punch", "category": "Drinks", "price_inr": 149, "price_aud": 7.99, "is_veg": True},

    # SAAR / SOUP
    {"name": "Tomato Saar", "description": "Kickstart your meal with the refreshing flavors of our Tomato Saar. Made with ripe tomatoes, onions, and a hint of black pepper", "category": "Soup & Saar", "price_inr": 229, "price_aud": None, "is_veg": True},
    {"name": "Vedik Soup", "description": "A light, nourishing soup made with ancient grains like jowar, bajra, and raagi flour, gently flavoured with cumin and mild spices", "category": "Soup & Saar", "price_inr": 269, "price_aud": 12.99, "is_veg": True},
    {"name": "Daal Soup", "description": "A comforting lentil soup slow-cooked with mild spices and a touch of ghee. Hearty yet light", "category": "Soup & Saar", "price_inr": 229, "price_aud": 12.99, "is_veg": True},
    {"name": "Pumpkin Soup (Only Sunday)", "description": "A smooth and velvety pumpkin soup made with fresh pumpkin and subtle seasoning. Naturally sweet, warm, and comforting", "category": "Soup & Saar", "price_inr": 269, "price_aud": 12.99, "is_veg": True},
    {"name": "Pandhara Rassa", "description": "A creamy coconut-based soup delicately flavoured with white pepper and mild spices. Smooth, warming, and gently spiced", "category": "Soup & Saar", "price_inr": 249, "price_aud": 12.99, "is_veg": True},

    # SNACKS
    {"name": "Kanda Bhaji (20 pcs)", "description": "Crispy onion fritters served hot with tamarind chutney – a monsoon classic", "category": "Snacks", "price_inr": 179, "price_aud": 12.99, "is_veg": True},
    {"name": "Maaswadi (4 pcs)", "description": "Gram flour rolls filled with a spicy coconut and peanut mix, served with curry", "category": "Snacks", "price_inr": 279, "price_aud": 19.99, "is_veg": True},
    {"name": "Sabudana Vada (4 pcs)", "description": "Crispy sago and potato patties – crunchy outside, soft inside", "category": "Snacks", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Snacks Platter (4 pcs)", "description": "The best for families who wish to explore variety of snacks together", "category": "Snacks", "price_inr": 599, "price_aud": None, "is_veg": True},
    {"name": "Snacks Platter (6 pcs)", "description": "The best for families who wish to explore variety of snacks together", "category": "Snacks", "price_inr": 699, "price_aud": None, "is_veg": True},
    {"name": "Snacks Platter (9 pcs)", "description": "The best for families who wish to explore variety of snacks together", "category": "Snacks", "price_inr": 1099, "price_aud": None, "is_veg": True},
    {"name": "Batate Vada (4 pcs)", "description": "Classic potato fritters seasoned with spices and fried until golden brown – a street food favourite", "category": "Snacks", "price_inr": 219, "price_aud": 15.99, "is_veg": True},
    {"name": "Kachori (6 pcs)", "description": "Deep-fried pastry pockets filled with spiced green peas – crunchy and flavourful", "category": "Snacks", "price_inr": 239, "price_aud": 16.99, "is_veg": True},
    {"name": "Pudachi Vadi (10 pcs)", "description": "Crispy gram flour rolls stuffed with coconut, coriander, and spices – deep-fried till golden. ONLY ON WEDNESDAY", "category": "Snacks", "price_inr": 239, "price_aud": 17.99, "is_veg": True},
    {"name": "Masala Bread Pakoda", "description": "Spiced version of bread fritters stuffed with seasoned potato mix – crisp and hearty", "category": "Snacks", "price_inr": 149, "price_aud": 10.99, "is_veg": True},
    {"name": "Vada Pav", "description": "Spiced potato fritter served in a soft bun with tangy chutney and a fried green chilli", "category": "Snacks", "price_inr": 55, "price_aud": 5.99, "is_veg": True},
    {"name": "Kanda Pohe", "description": "Flaked rice cooked with onions, peanuts, mustard seeds, curry leaves, and mild spices – a light and wholesome breakfast", "category": "Snacks", "price_inr": 169, "price_aud": 11.99, "is_veg": True},
    {"name": "Tarri Pohe", "description": "Flaked rice with spicy curry", "category": "Snacks", "price_inr": 189, "price_aud": 13.99, "is_veg": True},
    {"name": "Dadpe Pohe", "description": "Very old recipe of rice flakes with coconut and curd", "category": "Snacks", "price_inr": 169, "price_aud": None, "is_veg": True},
    {"name": "Alu Vadi (8 pcs)", "description": "Indulge in AluVadi—a savory roll of tantalizing taro leaves, spiced to perfection for a delectable Maharashtrian treat", "category": "Snacks", "price_inr": 239, "price_aud": 17.99, "is_veg": True},
    {"name": "Kothimbir Vadi (10 pcs)", "description": "Coriander and gram flour cakes steamed, then lightly fried for a crunchy texture", "category": "Snacks", "price_inr": 239, "price_aud": 17.99, "is_veg": True},
    {"name": "Vada Sample", "description": "Potato fritters served with spicy curry, chopped onion, and crunchy sev", "category": "Snacks", "price_inr": 149, "price_aud": 12.99, "is_veg": True},
    {"name": "Bread Pakoda", "description": "Triangular shape Bread dipped in gram flour batter, and fried golden brown served with tamarind chutney", "category": "Snacks", "price_inr": 129, "price_aud": 8.99, "is_veg": True},
    {"name": "Ukad", "description": "Savor the simplicity of Fodanichi Ukad steamed, spiced, and sublime, a Maharashtrian snack that comforts with every bite", "category": "Snacks", "price_inr": 199, "price_aud": None, "is_veg": True},
    {"name": "Kaccha Chiwada", "description": "Tea time snacks made with flaked rice and chopped onion, tomato & lavangi mirchi", "category": "Snacks", "price_inr": 119, "price_aud": None, "is_veg": True},
    {"name": "Papad Bowl", "description": "Explore flavors with our Papad Bowl—seasonal papads in a symphony of crunch and zest", "category": "Snacks", "price_inr": 129, "price_aud": None, "is_veg": True},
    {"name": "Mataki Bhel", "description": "Sprouted lentil salad mixed with chutneys, spices, and crispy toppings for a tangy street-style flavour", "category": "Snacks", "price_inr": 169, "price_aud": 12.99, "is_veg": True},

    # FASTING
    {"name": "Sabudana Khichadi", "description": "Sabudana Khichadi, Sabudana Usal - tastes amazing with potato slices and very spicy lemon pickle", "category": "Fasting", "price_inr": 169, "price_aud": 12.99, "is_veg": True},
    {"name": "Sabudana Thalipith", "description": "Peanut and upvas powder based pancakes made with upvas flour, spices & curd, deliciously savoured", "category": "Fasting", "price_inr": 199, "price_aud": 14.99, "is_veg": True},
    {"name": "Upvas Thalipith", "description": "The best combos of different fasting grains only is used to make this bhajani for fasting people", "category": "Fasting", "price_inr": 199, "price_aud": 14.99, "is_veg": True},
    {"name": "Rajgeera Thalipith", "description": "Upvas Thalipith served with Upvas Chutney and curd", "category": "Fasting", "price_inr": 199, "price_aud": None, "is_veg": True},
    {"name": "Fasting Thali", "description": "Fasting thali Served with 10+ items curated for the wholesome meal on your fasting day", "category": "Fasting", "price_inr": 499, "price_aud": None, "is_veg": True},

    # HEAVY BRUNCH
    {"name": "Thalipith (2 pc)", "description": "Made from mixed grain flour, this savory pancake has been part of all Marathi homes for a long time", "category": "Heavy Brunch", "price_inr": 199, "price_aud": 8.99, "is_veg": True},
    {"name": "Ghavan (3 pc)", "description": "A thin Rice Flour Pan Cake from the Konkan region of Maharashtra", "category": "Heavy Brunch", "price_inr": 199, "price_aud": None, "is_veg": True},
    {"name": "Dhirde (3 pc)", "description": "Garlic based pancakes made with wheat and gram flour, spices & curd, deliciously savoured", "category": "Heavy Brunch", "price_inr": 199, "price_aud": None, "is_veg": True},
    {"name": "Misal Pav", "description": "Spicy mixed lentil curry topped with farsan, served with soft bread rolls - originates from Nashik region", "category": "Heavy Brunch", "price_inr": 199, "price_aud": 14.99, "is_veg": True},
    {"name": "Ukarpendi", "description": "Made out of Wheat flour, curd, hot water onion served with pickle & curd", "category": "Heavy Brunch", "price_inr": 149, "price_aud": None, "is_veg": True},
    {"name": "Masala Varan Fal", "description": "One of the favorite preparations in Maharashtrian houses, Masala Varanfal", "category": "Heavy Brunch", "price_inr": 349, "price_aud": None, "is_veg": True},
    {"name": "Shrikhanda Puri Bhaji", "description": "Sweet yoghurt dessert served with puris and spiced potato curry - ideal combination", "category": "Heavy Brunch", "price_inr": 249, "price_aud": 17.99, "is_veg": True},
    {"name": "Aloocha Paratha (1 pc)", "description": "Soft flatbread stuffed with seasoned mashed potatoes – served with pickle and curd", "category": "Heavy Brunch", "price_inr": 149, "price_aud": 7.99, "is_veg": True},
    {"name": "Varan Fal", "description": "Small wheat dumplings cooked in a rich yellow lentil curry, a comforting homestyle dish", "category": "Heavy Brunch", "price_inr": 299, "price_aud": 20.99, "is_veg": True},
    {"name": "Puri Bhaji", "description": "Deep-fried bread served with dry spiced potato curry", "category": "Heavy Brunch", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Shengole", "description": "Spicy gram and wheat flour rings cooked in curry, served hot. ONLY ON THURSDAY", "category": "Heavy Brunch", "price_inr": 299, "price_aud": 20.99, "is_veg": True},

    # BHAKAR COMBOS
    {"name": "Shev Bhaji Combo", "description": "Crunchy chickpea noodles in a rich curry, served with bhakar", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 20.99, "is_veg": True},
    {"name": "Patodi Rassa Combo", "description": "Gram flour rolls in spicy curry good with bhakar and chilli paste", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 20.99, "is_veg": True},
    {"name": "Maaswadi Rassa Combo", "description": "Spicy besan rolls with peanut filling, served in red curry good with bhakar", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 20.99, "is_veg": True},
    {"name": "Vangyacha Bharit Combo (Saturday)", "description": "Roasted eggplant mash served with bhakar, brinjal curry, and yoghurt", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 20.99, "is_veg": True},
    {"name": "Ravan Pithala Combo", "description": "Extra spicy version of gram flour curry good with bhakar, curd, and chutney", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 19.99, "is_veg": True},
    {"name": "Pithala (Yellow) Combo", "description": "Creamy gram flour curry with millet bread and brinjal curry – a rustic classic", "category": "Bhakar Combo", "price_inr": 319, "price_aud": 19.99, "is_veg": True},
    {"name": "Pali Pithala Combo", "description": "Watery gram flour curry served with millet flatbread – authentic rustic style", "category": "Bhakar Combo", "price_inr": 319, "price_aud": 19.99, "is_veg": True},
    {"name": "Zhunka Combo", "description": "Spiced gram flour stir-fry served with millet flatbread, brinjal curry, and chilli chutney", "category": "Bhakar Combo", "price_inr": 319, "price_aud": 19.99, "is_veg": True},
    {"name": "Kaju Curry Combo", "description": "Creamy cashew nut curry paired with millet bread – rich and satisfying", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 21.99, "is_veg": True},
    {"name": "Poli Bhaji Combo", "description": "Three pc Wheat chapati, dal, curry of the day with pickle homefood go good with buttermilk", "category": "Bhakar Combo", "price_inr": 349, "price_aud": 20.99, "is_veg": True},

    # BHAJI
    {"name": "Ravan Pithala", "description": "Extra spicy version of pithala made with chilli and curd", "category": "Bhaji", "price_inr": 379, "price_aud": 20.99, "is_veg": True},
    {"name": "Pithala (Yellow)", "description": "Thick gram flour curry – comforting and mildly spiced", "category": "Bhaji", "price_inr": 379, "price_aud": 20.99, "is_veg": True},
    {"name": "Bharit (Saturdays)", "description": "Brinjal bharit is one of the most authentic recipes of Purnabramha", "category": "Bhaji", "price_inr": 379, "price_aud": 23.99, "is_veg": True},
    {"name": "Dal Vanga", "description": "Brinjal prep with Tur dal and spices served with three fulkas", "category": "Bhaji", "price_inr": 389, "price_aud": None, "is_veg": True},
    {"name": "Mix Cauliflower Bhaji", "description": "Mix Vegetable, just like homemade preparation", "category": "Bhaji", "price_inr": 389, "price_aud": None, "is_veg": True},
    {"name": "Chef Special Bhaji", "description": "The best of all, our chef special Bhaji served in three different spice levels", "category": "Bhaji", "price_inr": 389, "price_aud": 23.99, "is_veg": True},
    {"name": "Shev Bhaji", "description": "A musthave piping hot curry made up with gram flour and boiled it in curry", "category": "Bhaji", "price_inr": 379, "price_aud": 23.99, "is_veg": True},
    {"name": "Patodi Rassa", "description": "Whole red lentils simmered in black masala gravy – earthy and spicy", "category": "Bhaji", "price_inr": 399, "price_aud": 24.99, "is_veg": True},
    {"name": "Maaswadi Rassa", "description": "Crispy chickpea noodles cooked in spicy curry – a Maharashtra favourite", "category": "Bhaji", "price_inr": 399, "price_aud": 24.99, "is_veg": True},
    {"name": "Patal Bhaji (Sundays)", "description": "Mixed greens curry made with chana dal and spinach or colocasia leaves", "category": "Bhaji", "price_inr": 379, "price_aud": 23.99, "is_veg": True},
    {"name": "Mungwadi Rassa", "description": "Classic recipe of moong dal vadis cooked in gravy of tomato, blended with onion and spice powder", "category": "Bhaji", "price_inr": 389, "price_aud": None, "is_veg": True},
    {"name": "Bharli Vangi", "description": "Stuffed baby eggplants cooked in rich, spiced coconut & Peanut gravy", "category": "Bhaji", "price_inr": 349, "price_aud": 24.99, "is_veg": True},
    {"name": "Zhunka", "description": "Spiced chickpea flour stir-fry with onions – a traditional rustic dish", "category": "Bhaji", "price_inr": 289, "price_aud": 20.99, "is_veg": True},
    {"name": "Kaju Curry", "description": "Cashew and dry fruit curry in creamy, mildly sweet sauce", "category": "Bhaji", "price_inr": 479, "price_aud": 26.99, "is_veg": True},
    {"name": "Akkha Masur", "description": "Whole Masur Dal in spicy maharashtrian black masala, good with dupodi poli", "category": "Bhaji", "price_inr": 379, "price_aud": 22.99, "is_veg": True},
    {"name": "Kadhi Gole", "description": "Kadhi Gole - soothing gram flour balls dipped & cooked in Kadhi. A Non Spicy preparation", "category": "Bhaji", "price_inr": 349, "price_aud": 20.99, "is_veg": True},
    {"name": "Dry / Jeera Aloo", "description": "Potatoes tossed in cumin seeds and mild spices – a simple comfort dish", "category": "Bhaji", "price_inr": 249, "price_aud": 17.99, "is_veg": True},
    {"name": "Matki Usal / Barbati Usal", "description": "Sprouted lentils cooked in a spicy onion-tomato sauce, garnished with coriander", "category": "Bhaji", "price_inr": 299, "price_aud": 20.99, "is_veg": True},

    # VARAN / DAL
    {"name": "Mataki Amti", "description": "Spicy sprouted lentil curry in tangy gravy – full of protein", "category": "Dal", "price_inr": 249, "price_aud": 15.99, "is_veg": True},
    {"name": "Lasun Varan", "description": "Garlic-flavoured lentil curry with green chillies – aromatic and comforting", "category": "Dal", "price_inr": 249, "price_aud": 14.99, "is_veg": True},
    {"name": "Sadha Varan", "description": "Plain yellow lentil curry with mild tempering of garlic and green chilli", "category": "Dal", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Takachi Kadhi", "description": "Tangy yoghurt-based curry thickened with gram flour – light and refreshing", "category": "Dal", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Kataachi Amti", "description": "Spicy lentil soup made from chana dal with coconut and special masalas", "category": "Dal", "price_inr": 249, "price_aud": 15.99, "is_veg": True},
    {"name": "Jeera Varan", "description": "Lentil curry with cumin seasoning – simple and fragrant", "category": "Dal", "price_inr": 249, "price_aud": 14.99, "is_veg": True},
    {"name": "Chef Special Dal", "description": "Tur dal tempered with garlic and spices – homestyle and mild", "category": "Dal", "price_inr": 289, "price_aud": 17.99, "is_veg": True},

    # RICE
    {"name": "Steam Rice", "description": "The simplest form of rice, just steamed at right temperature to give you the complete feelings of Purnabramha", "category": "Rice", "price_inr": 199, "price_aud": 9.99, "is_veg": True},
    {"name": "Dahi Bhat", "description": "Creamy yoghurt rice with tempered mustard seeds and curry leaves", "category": "Rice", "price_inr": 219, "price_aud": 11.99, "is_veg": True},
    {"name": "Kanda Rice", "description": "Rice cooked with onions, turmeric, and mild spices", "category": "Rice", "price_inr": 219, "price_aud": 11.99, "is_veg": True},
    {"name": "Tup Bhat", "description": "Chef special Rice tossed in Desi Ghee, Black Pepper, Cloves and Dry Fruits", "category": "Rice", "price_inr": 249, "price_aud": 17.99, "is_veg": True},
    {"name": "Bhaji Bhat", "description": "Spiced rice cooked with green leafy vegetables – served with kadhi or tamarind sauce", "category": "Rice", "price_inr": 249, "price_aud": 17.99, "is_veg": True},
    {"name": "Gola Bhat", "description": "Rice served with steamed gram flour dumplings in spicy sauce", "category": "Rice", "price_inr": 249, "price_aud": 17.99, "is_veg": True},
    {"name": "Ravan Bhat", "description": "Spicy and tangy rice with a bold flavour kick", "category": "Rice", "price_inr": 249, "price_aud": 17.99, "is_veg": True},
    {"name": "Masale Bhat", "description": "Spiced rice cooked with vegetables and traditional Maharashtrian masala", "category": "Rice", "price_inr": 299, "price_aud": 17.99, "is_veg": True},
    {"name": "Tup Varan Bhat", "description": "Fragrant ghee rice with pepper, cloves, and dry fruits", "category": "Rice", "price_inr": 249, "price_aud": 15.99, "is_veg": True},
    {"name": "Khajur Bhat", "description": "Rice flavored with Dates and House's Secret Spice Mixes", "category": "Rice", "price_inr": 299, "price_aud": None, "is_veg": True},
    {"name": "Rice Platter", "description": "Rice with all options as platter min 3 rice type will come as part of plate", "category": "Rice", "price_inr": 399, "price_aud": None, "is_veg": True},

    # ROTI
    {"name": "Fulka", "description": "Soft whole-wheat flatbread topped with ghee", "category": "Roti", "price_inr": 29, "price_aud": 2.99, "is_veg": True},
    {"name": "Dupodi Poli (Chapati)", "description": "Layered whole-wheat flatbread – soft and chewy", "category": "Roti", "price_inr": 32, "price_aud": 3.99, "is_veg": True},
    {"name": "Jowar / Bajara Bhakar", "description": "Traditional millet flatbread served warm with ghee", "category": "Roti", "price_inr": 59, "price_aud": 4.99, "is_veg": True},
    {"name": "Wade (2 pcs)", "description": "Special steamed and fried prep for vade", "category": "Roti", "price_inr": 79, "price_aud": None, "is_veg": True},
    {"name": "Rice Bhakar", "description": "Rice flour flatbread – soft and chewy, pairs well with spicy curries", "category": "Roti", "price_inr": 59, "price_aud": 4.99, "is_veg": True},
    {"name": "Puri Set (5 pcs)", "description": "Five deep-fried wheat bread rounds, served fresh", "category": "Roti", "price_inr": 99, "price_aud": 8.99, "is_veg": True},

    # SWEETS
    {"name": "Modak", "description": "Stuffing made out of coconut & jaggery and stuffed in rice flour dough in a typical shape and steamed", "category": "Sweets", "price_inr": 249, "price_aud": 18.99, "is_veg": True},
    {"name": "Shrikhanda", "description": "Shrikhand, an Indian sweetmeat made of hung Curd alongwith perfectly blended sugar, cardamom powder & kesar", "category": "Sweets", "price_inr": 199, "price_aud": 12.99, "is_veg": True},
    {"name": "Shirvale", "description": "Ras Shirvale or Shirwale is a traditional Marathi recipe from Konkan villages. made out of rice flour, and coconut milk", "category": "Sweets", "price_inr": 389, "price_aud": 14.99, "is_veg": True},
    {"name": "Puranpoli", "description": "Puranpoli's significance is mainly during the festival of Holi", "category": "Sweets", "price_inr": 119, "price_aud": 10.99, "is_veg": True},
    {"name": "Khava Poli", "description": "Milk reduced to almost one fifth of it's consistency to form Khava which is widely used for making variety of Indian sweets", "category": "Sweets", "price_inr": 119, "price_aud": 10.99, "is_veg": True},
    {"name": "Tilgul Poli", "description": "An awesome delight for ones with a sweet tooth. Tilgul poli, made of sesame seeds & jaggery with flavour of cardamom & nutmeg", "category": "Sweets", "price_inr": 119, "price_aud": None, "is_veg": True},
    {"name": "Kharvas", "description": "The first Cow milk pie made out in our own godhan shala in Pune", "category": "Sweets", "price_inr": 439, "price_aud": None, "is_veg": True},
    {"name": "Aamras (Seasonal)", "description": "Sweet dessert made out of mangos", "category": "Sweets", "price_inr": 210, "price_aud": 11.99, "is_veg": True},
    {"name": "Amrakhanda", "description": "Amrakhanda an Indian sweetmeat made of hung Curd along with perfectly blended sugar, cardamom powder & kesar and Mango flavor", "category": "Sweets", "price_inr": 219, "price_aud": 13.99, "is_veg": True},
    {"name": "Sheera (Rava)", "description": "The best simple preparation of Rava (semolina) sugar and khoya and milk", "category": "Sweets", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Basundi", "description": "Basundi, is the signature recipe of our Chef prepared out of reduced milk and flavoured with Cardamom & garnished with almonds", "category": "Sweets", "price_inr": 199, "price_aud": 14.99, "is_veg": True},
    {"name": "Shewaya Kheer", "description": "The Rava and rice floor dough made in thin layered spaghetti shaped boiled in milk till cooked and served with dryfruits", "category": "Sweets", "price_inr": 199, "price_aud": 13.99, "is_veg": True},
    {"name": "Chirote (6 pcs)", "description": "Chiroti is a delicacy predominantly served in Maharashtra as well as Karnataka", "category": "Sweets", "price_inr": 249, "price_aud": None, "is_veg": True},
    {"name": "Mungdal Halwa", "description": "Mungdal halwa made with mungdal pure desi ghee and khoya", "category": "Sweets", "price_inr": 249, "price_aud": None, "is_veg": True},
    {"name": "Gulshela", "description": "Typical Nagpuri style Dessert made out of milk, Yellow Pumpkin, jaggery and little sugar", "category": "Sweets", "price_inr": 249, "price_aud": None, "is_veg": True},
    {"name": "Gajar Halwa (Seasonal)", "description": "Gajar ka halwa is a combination of nuts, milk, sugar, khoya and ghee with grated carrot", "category": "Sweets", "price_inr": 218, "price_aud": None, "is_veg": True},
    {"name": "Gulabjam (3 pcs)", "description": "Gulabjam specially made with pure ingredients and process", "category": "Sweets", "price_inr": 199, "price_aud": None, "is_veg": True},

    # SPECIAL THALIS
    {"name": "Shree Shiv Thali (Monday)", "description": "Sabudana Vada & Mungacha Vada, Ladyfinger/Rani Palak/Tinda/Aloo Curry, Dal & Kadhi, Fulka, Steam Rice & Curd Rice, Shrikhand & Chirote", "category": "Special Thalis", "price_inr": 499, "price_aud": None, "is_veg": True},
    {"name": "Shree Swami Samrath Thali (Tuesday)", "description": "Sabudana Vada & Goti Vada, Bottle Gourd with Dal Channa & Mugwadi Rassa, Dal & Kadhi, Fulka, Steam Rice & Kande Rice, Mungdal Halwa & Basundi", "category": "Special Thalis", "price_inr": 499, "price_aud": None, "is_veg": True},
    {"name": "Shree Vithayee Thali (Wednesday)", "description": "Sabudana Vada & Appa Pakoda, Cabbage Potato, Sev Bhaji, Dal & Kadhi, Fulka, Steam Rice & Ravan Bhat, Shewaya Kheer & Rava Sheera", "category": "Special Thalis", "price_inr": 499, "price_aud": None, "is_veg": True},
    {"name": "Shree Duttaguru Thali (Thursday)", "description": "Sabudana Vada & Kothimbir Vadi, Flower Potato & Brinjal Curry, Dal & Kadhi, Fulka, Steam Rice & Golabhat, Naralacha Ladu & Mung Dal Halwa", "category": "Special Thalis", "price_inr": 499, "price_aud": None, "is_veg": True},
    {"name": "Shree Balaji Thali (Friday)", "description": "Sabudana Vada Or Mung Bhaji, Menthi Alan & Ridge Gourd, Dal Kadhi & Dal, Fulka, Steam Rice & Veg Pulav, Gulshela Diva & Satori", "category": "Special Thalis", "price_inr": 549, "price_aud": None, "is_veg": True},
    {"name": "Shree Gajanan Maharaj Thali (Saturday)", "description": "Sabudana Vada & Mutter Kachori, Patodi Rassa & Baingan Bharta, Dal & Kadhi, Fulka, Steam Rice & Bhajjibhat, Basundi & Shirvale", "category": "Special Thalis", "price_inr": 549, "price_aud": None, "is_veg": True},
    {"name": "Shree Mahalakshmi Thali (Sunday)", "description": "Sabudana Vada & Palak Bhaji, Kohala (Pumpkin) Curry & Patal Bhaji, Dal & Kadhi, Fulka, Steam Rice & Masale Bhat, Modak & Puranpoli", "category": "Special Thalis", "price_inr": 549, "price_aud": None, "is_veg": True},
    {"name": "Day Special Thali", "description": "Day Sp. thali Served as non-shareable with two curries, two dals, two rice, and puri or bhakar or chapati, papad, sweet, snacks two", "category": "Special Thalis", "price_inr": None, "price_aud": 35.99, "is_veg": True},
    {"name": "Misal Thali", "description": "Misal thali is for all misal lovers who like to have misal curry unlimited", "category": "Special Thalis", "price_inr": 449, "price_aud": 29.99, "is_veg": True},
    {"name": "Varhadi Thali", "description": "Starters, Roti, Sabji, Rice(Plain & Spl.), Sweet & Extra Zunka, Bharli Vangi & Bhakri", "category": "Special Thalis", "price_inr": 549, "price_aud": None, "is_veg": True},
    {"name": "Vidharbha Thali", "description": "Bhakar, Brinjalcurry, zhunka, Kothimber vadi Masala Bhat, & shrikhanda and all sides", "category": "Special Thalis", "price_inr": 549, "price_aud": 39.99, "is_veg": True},
    {"name": "Purankut Thali", "description": "2 Purnapoli, Ghee & a bowl of Milk. Batatavada & Mirchi bhaji A bowl of Kat Pickle, Papad, Steam Rice & Fried Mirchi", "category": "Special Thalis", "price_inr": 549, "price_aud": 39.99, "is_veg": True},
    {"name": "Shravan Maas Thali", "description": "A festive thali featuring masala puri (4 pcs), your choice of masala bhat, dahi bhat, patodi rassa, or seasonal bhaji; served with gulab jamun, batata vada, buttermilk, kothimbir vadi or aluvadi, pickle, papad, and fried chilli", "category": "Special Thalis", "price_inr": 549, "price_aud": 39.99, "is_veg": True},
    {"name": "Meva Thali", "description": "An Exclusive Thali, designed for Meva Lovers and can also be enjoyed by Balgopals", "category": "Special Thalis", "price_inr": 749, "price_aud": None, "is_veg": True},
    {"name": "Puri Special Thali", "description": "With Sweet and Snack, 3 Puri, rice, sp.rice, dal, sabji 1, sabji 2, kadhi, koshimbir/salad, pickle", "category": "Special Thalis", "price_inr": 549, "price_aud": None, "is_veg": True},
    {"name": "Rodaga Thali", "description": "Rodaga Thali Special Rodaga, Vangi Vegetable, Mirchy Dal, Kaniksheera, Sadha bhat, Tup, Gul, Thecha, Shrikhanda", "category": "Special Thalis", "price_inr": 549, "price_aud": None, "is_veg": True},

    # SIDES
    {"name": "Day Sp. Koshimbeer", "description": "Fresh daily special salad", "category": "Sides", "price_inr": None, "price_aud": 4.99, "is_veg": True},
    {"name": "Green Salad", "description": "Fresh green vegetables", "category": "Sides", "price_inr": None, "price_aud": 4.99, "is_veg": True},
    {"name": "Thecha", "description": "Spicy green chilli condiment", "category": "Sides", "price_inr": None, "price_aud": 1.99, "is_veg": True},
    {"name": "Curd", "description": "Fresh yogurt", "category": "Sides", "price_inr": None, "price_aud": 2.99, "is_veg": True},
    {"name": "Extra Green Chutney", "description": "Fresh coriander mint chutney", "category": "Sides", "price_inr": None, "price_aud": 2.99, "is_veg": True},
    {"name": "Extra Tamarind Chutney", "description": "Sweet and tangy tamarind chutney", "category": "Sides", "price_inr": None, "price_aud": 2.99, "is_veg": True},
    {"name": "Extra Pav / Roasted", "description": "Additional bread roll", "category": "Sides", "price_inr": None, "price_aud": 1.49, "is_veg": True},
    {"name": "Papad (2 pc)", "description": "Crispy lentil crackers", "category": "Sides", "price_inr": None, "price_aud": 1.99, "is_veg": True},
    {"name": "Lasun Chutney", "description": "Spicy garlic chutney", "category": "Sides", "price_inr": None, "price_aud": 3.99, "is_veg": True},
    {"name": "Methkut", "description": "Traditional Maharashtrian spice powder", "category": "Sides", "price_inr": None, "price_aud": 3.99, "is_veg": True},
    {"name": "Pickle", "description": "Traditional Indian pickle", "category": "Sides", "price_inr": None, "price_aud": 2.99, "is_veg": True},
    {"name": "Peanut Chutney", "description": "Ground peanut chutney", "category": "Sides", "price_inr": None, "price_aud": 3.99, "is_veg": True},
    {"name": "Sesame Chutney", "description": "Til (sesame) based chutney", "category": "Sides", "price_inr": None, "price_aud": 3.99, "is_veg": True},
    {"name": "Onion Salad", "description": "Fresh onion rings with lemon", "category": "Sides", "price_inr": None, "price_aud": 4.99, "is_veg": True},
]

# Locations data
LOCATIONS_DATA = [
    {
        "name": "PB-HSR Layout",
        "city": "Bengaluru",
        "country": "India",
        "address": "No 1, 14th Main Road, Sector 4, HSR Layout, Bengaluru - 560102",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Sambhajinagar",
        "city": "Sambhajinagar",
        "country": "India",
        "address": "Shop No.5, Ground Floor, Near HDFC Bank, Sambhajinagar",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Kharadi",
        "city": "Pune",
        "country": "India",
        "address": "Ground Floor, EON Free Zone, Kharadi, Pune - 411014",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Hinjawadi",
        "city": "Pune",
        "country": "India",
        "address": "Shop No.2, Opposite Infosys Gate 3, Hinjawadi Phase 1, Pune",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Thane",
        "city": "Thane",
        "country": "India",
        "address": "Ground Floor, Viviana Mall, Eastern Express Highway, Thane",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Dombivali",
        "city": "Dombivali",
        "country": "India",
        "address": "Shop No.10, Station Road, Dombivali East",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Kalyan",
        "city": "Kalyan",
        "country": "India",
        "address": "Near Kalyan Railway Station, Kalyan West",
        "phone": "+91 9741399190",
        "whatsapp": "+91 9741399190",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    },
    {
        "name": "PB-Perth",
        "city": "Perth",
        "country": "Australia",
        "address": "123 Murray Street, Perth WA 6000, Australia",
        "phone": "+61 1234567890",
        "whatsapp": "+61 1234567890",
        "google_review_link": "https://g.page/r/CQxxxxxxxxx/review",
        "is_active": True
    }
]

async def seed_database():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Clear existing data
    print("Clearing existing menu items...")
    await db.menu_items.delete_many({})
    
    print("Clearing existing locations...")
    await db.locations.delete_many({})
    
    # Create admin user if not exists
    print("Creating admin user...")
    existing_admin = await db.users.find_one({"email": "admin@purnabramha.com"})
    if not existing_admin:
        import bcrypt
        hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_user = {
            "id": str(uuid.uuid4()),
            "email": "admin@purnabramha.com",
            "name": "Admin",
            "phone": "9741399190",
            "password": hashed_password,
            "role": "admin",
            "created_at": "2025-01-01T00:00:00Z"
        }
        await db.users.insert_one(admin_user)
        print("Admin user created: admin@purnabramha.com / admin123")
    else:
        print("Admin user already exists")
    
    # Insert menu items
    print(f"Inserting {len(MENU_DATA)} menu items...")
    for item in MENU_DATA:
        menu_item = {
            "id": str(uuid.uuid4()),
            "name": item["name"],
            "description": item["description"],
            "category": item["category"],
            "price": item["price_inr"] or item["price_aud"] or 0,
            "price_inr": item["price_inr"],
            "price_aud": item["price_aud"],
            "image_url": None,
            "is_veg": item["is_veg"],
            "is_available": True
        }
        await db.menu_items.insert_one(menu_item)
    
    print(f"Inserted {len(MENU_DATA)} menu items")
    
    # Insert locations
    print(f"Inserting {len(LOCATIONS_DATA)} locations...")
    for loc in LOCATIONS_DATA:
        location = {
            "id": str(uuid.uuid4()),
            **loc
        }
        await db.locations.insert_one(location)
    
    print(f"Inserted {len(LOCATIONS_DATA)} locations")
    
    client.close()
    print("\nDatabase seeding completed!")
    print("\n=== Admin Credentials ===")
    print("Email: admin@purnabramha.com")
    print("Password: admin123")
    print("========================")

if __name__ == "__main__":
    asyncio.run(seed_database())
