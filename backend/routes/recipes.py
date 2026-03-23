# =======================================
# Recipes & Bhojan Guru Routes
# Recipe CRUD, Bhojan Guru Suggestions, Body Need Recommendations
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Recipes & Bhojan Guru"])

# ROOT_DIR for data files
ROOT_DIR = None

def set_root_dir(path):
    global ROOT_DIR
    ROOT_DIR = path

# Verify token function (set from main server)
verify_token = None

def set_verify_token(func):
    global verify_token
    verify_token = func

# =======================================
# DATA LOADING FUNCTIONS
# =======================================

def load_recipe_data():
    recipe_file = ROOT_DIR / "recipes_db.json"
    if recipe_file.exists():
        with open(recipe_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"categories": [], "recipes": {}}

def load_description_data():
    desc_file = ROOT_DIR / "description_data.json"
    if desc_file.exists():
        with open(desc_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_bhojan_guru_data():
    bhojan_file = ROOT_DIR / "bhojan_guru_data.json"
    if bhojan_file.exists():
        with open(bhojan_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"bhojanGuru": {}, "regionWise": {}, "bodyNeedMatrix": {}}

def save_recipe_data(data: dict):
    """Save recipe data to JSON file"""
    recipe_file = ROOT_DIR / "recipes_db.json"
    with open(recipe_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =======================================
# PYDANTIC MODELS
# =======================================

class RecipeCreate(BaseModel):
    key: str
    name: str
    display: str
    ingredients: List[str] = []
    method: List[str] = []
    category: str = "MAINS"
    image: Optional[str] = ""

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    display: Optional[str] = None
    ingredients: Optional[List[str]] = None
    method: Optional[List[str]] = None
    category: Optional[str] = None
    image: Optional[str] = None

# =======================================
# RECIPE ROUTES
# =======================================

@router.get("/recipes")
async def get_recipes():
    """Get all recipes with ingredients and methods"""
    data = load_recipe_data()
    return {
        "categories": data.get("categories", []),
        "recipes": data.get("recipes", {}),
    }

@router.get("/descriptions")
async def get_descriptions():
    """Get all menu item descriptions in English and Marathi"""
    return {"descriptions": load_description_data()}

@router.get("/recipes/categories")
async def get_recipe_categories():
    """Get all recipe categories"""
    data = load_recipe_data()
    return {"categories": data.get("categories", [])}

@router.get("/recipes/search")
async def search_recipes(q: str = ""):
    """Search recipes by name or display"""
    data = load_recipe_data()
    recipes = data.get("recipes", {})
    
    if not q:
        return {"recipes": recipes}
    
    q_lower = q.lower()
    filtered = {}
    for key, recipe in recipes.items():
        name = recipe.get("name", "").lower()
        display = recipe.get("display", "").lower()
        category = recipe.get("category", "").lower()
        if q_lower in name or q_lower in display or q_lower in key or q_lower in category:
            filtered[key] = recipe
    
    return {"recipes": filtered}

@router.post("/recipes")
async def create_recipe(req: RecipeCreate, token: str):
    """Create a new recipe (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage recipes")
    
    data = load_recipe_data()
    
    if req.key in data.get("recipes", {}):
        raise HTTPException(400, f"Recipe '{req.key}' already exists")
    
    if "recipes" not in data:
        data["recipes"] = {}
    
    data["recipes"][req.key] = {
        "name": req.name,
        "display": req.display,
        "ingredients": req.ingredients,
        "method": req.method,
        "category": req.category.upper(),
        "image": req.image or ""
    }
    
    save_recipe_data(data)
    logger.info(f"Recipe created: {req.key} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Recipe '{req.display}' created successfully"}

@router.put("/recipes/{recipe_key}")
async def update_recipe(recipe_key: str, req: RecipeUpdate, token: str):
    """Update an existing recipe (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage recipes")
    
    data = load_recipe_data()
    
    if recipe_key not in data.get("recipes", {}):
        raise HTTPException(404, f"Recipe '{recipe_key}' not found")
    
    recipe = data["recipes"][recipe_key]
    if req.name is not None:
        recipe["name"] = req.name
    if req.display is not None:
        recipe["display"] = req.display
    if req.ingredients is not None:
        recipe["ingredients"] = req.ingredients
    if req.method is not None:
        recipe["method"] = req.method
    if req.category is not None:
        recipe["category"] = req.category.upper()
    if req.image is not None:
        recipe["image"] = req.image
    
    save_recipe_data(data)
    logger.info(f"Recipe updated: {recipe_key} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Recipe '{recipe_key}' updated successfully"}

@router.delete("/recipes/{recipe_key}")
async def delete_recipe(recipe_key: str, token: str):
    """Delete a recipe (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can manage recipes")
    
    data = load_recipe_data()
    
    if recipe_key not in data.get("recipes", {}):
        raise HTTPException(404, f"Recipe '{recipe_key}' not found")
    
    del data["recipes"][recipe_key]
    save_recipe_data(data)
    logger.info(f"Recipe deleted: {recipe_key} by {session.get('managerName')}")
    
    return {"success": True, "message": f"Recipe '{recipe_key}' deleted successfully"}

# =======================================
# BHOJAN GURU ROUTES
# =======================================

@router.get("/bhojan_guru")
async def get_bhojan_guru():
    """Get Bhojan Guru recommendations data - mood/occasion/season based suggestions"""
    data = load_bhojan_guru_data()
    return {
        "bhojanGuru": data.get("bhojanGuru", {}),
        "regionWise": data.get("regionWise", {}),
        "bodyNeedMatrix": data.get("bodyNeedMatrix", {})
    }

@router.post("/bhojan_guru/suggest")
async def suggest_by_filters(
    mood: Optional[str] = None,
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    spice: Optional[str] = None
):
    """Get dish suggestions based on mood, occasion, season, and spice preference"""
    data = load_bhojan_guru_data()
    bhojan_guru = data.get("bhojanGuru", {})
    
    suggestions = []
    for key, item in bhojan_guru.items():
        score = 0
        
        if mood and mood.lower() in [m.lower() for m in item.get("mood", [])]:
            score += 2
        
        if occasion and occasion.lower() in [o.lower() for o in item.get("occasion", [])]:
            score += 2
        
        item_seasons = [s.lower() for s in item.get("season", [])]
        if season and (season.lower() in item_seasons or "all" in item_seasons):
            score += 1
        
        if spice and spice.lower() == item.get("spice", "").lower():
            score += 1
        
        if score > 0:
            suggestions.append({
                "key": key,
                "display": item.get("display"),
                "score": score,
                "mood": item.get("mood", []),
                "occasion": item.get("occasion", []),
                "spice": item.get("spice"),
                "tags": item.get("tags", []),
                "best_with": item.get("best_with", []),
                "combo": item.get("combo", []),
                "upsell": item.get("upsell", [])
            })
    
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    return {"suggestions": suggestions[:10]}

@router.get("/bhojan_guru/region/{day}")
async def get_region_recommendation(day: str):
    """Get region-wise thali recommendation for a specific day"""
    data = load_bhojan_guru_data()
    region_wise = data.get("regionWise", {})
    
    day_capitalized = day.capitalize()
    if day_capitalized in region_wise:
        return {"day": day_capitalized, "recommendation": region_wise[day_capitalized]}
    
    return {"day": day_capitalized, "recommendation": None, "message": "No recommendation for this day"}

@router.post("/bhojan_guru/body_need")
async def body_need_suggestion(
    energy: str = "normal",
    digestion: str = "normal",
    mood: str = "calm",
    spice: str = "mild",
    purpose: str = "family",
    weather: str = "any"
):
    """Generate food recommendation based on body needs (6 questions)"""
    data = load_bhojan_guru_data()
    matrix = data.get("bodyNeedMatrix", {})
    bhojan_guru = data.get("bhojanGuru", {})
    
    prefer_tags = set()
    avoid_tags = set()
    
    for category, value in [
        ("energy", energy),
        ("digestion", digestion),
        ("mood", mood),
        ("spice", spice),
        ("purpose", purpose),
        ("weather", weather)
    ]:
        if category in matrix and value in matrix[category]:
            prefer_tags.update(matrix[category][value].get("prefer", []))
            avoid_tags.update(matrix[category][value].get("avoid", []))
    
    recommendations = []
    for key, item in bhojan_guru.items():
        item_tags = set([t.lower() for t in item.get("tags", [])])
        item_tags.add(item.get("spice", "").lower())
        
        score = 0
        
        for pref in prefer_tags:
            if pref.lower() in item_tags or pref.lower() in key.lower():
                score += 1
        
        for avoid in avoid_tags:
            if avoid.lower() in item_tags or avoid.lower() in key.lower():
                score -= 2
        
        if digestion == "sensitive" and item.get("spice") in ["mild", "very mild", "sweet"]:
            score += 2
        
        if weather == "hot" and "cooling" in [m.lower() for m in item.get("mood", [])]:
            score += 2
        
        if mood == "stressed" and "comfort" in [m.lower() for m in item.get("mood", [])]:
            score += 2
        
        recommendations.append({
            "key": key,
            "display": item.get("display"),
            "score": score,
            "spice": item.get("spice"),
            "tags": item.get("tags", []),
            "best_with": item.get("best_with", [])
        })
    
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "recommendations": recommendations[:5],
        "preferences": list(prefer_tags),
        "avoidances": list(avoid_tags)
    }
