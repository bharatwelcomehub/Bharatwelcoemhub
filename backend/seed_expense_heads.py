#!/usr/bin/env python3
"""
Seed script to populate the expense_heads collection with default categories.
Run this once to ensure all expense categories are in the database.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Default expense heads
DEFAULT_EXPENSE_HEADS = [
    {"name": "GROCERY", "description": "Daily grocery items", "is_active": True},
    {"name": "DAIRY PRODUCTS", "description": "Milk, curd, paneer etc.", "is_active": True},
    {"name": "FRUITS & VEGETABLE", "description": "Fresh fruits and vegetables", "is_active": True},
    {"name": "WATER CAN / BOTTLE", "description": "Drinking water supplies", "is_active": True},
    {"name": "CYLINDER", "description": "Gas cylinders", "is_active": True},
    {"name": "PAV", "description": "Bread/Pav supplies", "is_active": True},
    {"name": "PACKAGING MATERIAL", "description": "Takeaway containers, bags", "is_active": True},
    {"name": "CELEBRATION EXPENSES", "description": "Festival and event expenses", "is_active": True},
    {"name": "MEDIA & ADVERTISEMENT", "description": "Marketing and ads", "is_active": True},
    {"name": "RESTAURANT GENERAL EXPENSES", "description": "Miscellaneous restaurant expenses", "is_active": True},
    {"name": "REPAIR & MAINTENANCE", "description": "Equipment and property repairs", "is_active": True},
    {"name": "SALARY", "description": "Staff salary payments", "is_active": True},
    {"name": "ADVANCE", "description": "Salary advances to staff", "is_active": True},
    {"name": "RENT", "description": "Shop/property rent", "is_active": True},
    {"name": "ELECTRICITY", "description": "Electricity bills", "is_active": True},
    {"name": "STATIONARY & PACKAGING", "description": "Office supplies and packaging", "is_active": True},
    {"name": "OVER TIME", "description": "Staff overtime payments", "is_active": True},
    {"name": "STAFF ROOM RENT", "description": "Staff accommodation rent", "is_active": True},
    {"name": "EMI / LOAN INSTALMENT", "description": "Loan EMI payments", "is_active": True},
    {"name": "RENT PAID SHOP", "description": "Main shop rent", "is_active": True},
    {"name": "TRAVELLING EXPENSES", "description": "Travel and conveyance", "is_active": True},
    {"name": "TELEPHONE & INTERNET", "description": "Phone and internet bills", "is_active": True},
    {"name": "PROFESSIONAL FEES", "description": "Legal, accounting, consulting fees", "is_active": True},
    {"name": "INSURANCE", "description": "Business insurance premiums", "is_active": True},
    {"name": "CLEANING & HYGIENE", "description": "Cleaning supplies and services", "is_active": True},
    {"name": "UNIFORM & SAFETY", "description": "Staff uniforms and safety equipment", "is_active": True},
    {"name": "PETTY CASH EXPENSES", "description": "Miscellaneous small expenses", "is_active": True},
    {"name": "BANK CHARGES", "description": "Bank fees and charges", "is_active": True},
    {"name": "INTEREST PAID", "description": "Interest on loans", "is_active": True},
    {"name": "OTHER EXPENSES", "description": "Miscellaneous other expenses", "is_active": True},
]


async def seed_expense_heads():
    """Seed the expense_heads collection with default categories."""
    
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    
    if not mongo_url or not db_name:
        print("ERROR: MONGO_URL or DB_NAME not found in environment")
        return False
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    try:
        # Check current count
        current_count = await db.expense_heads.count_documents({})
        print(f"Current expense_heads count: {current_count}")
        
        inserted = 0
        skipped = 0
        
        for head in DEFAULT_EXPENSE_HEADS:
            # Check if already exists
            existing = await db.expense_heads.find_one({"name": head["name"]})
            if existing:
                skipped += 1
                continue
            
            # Insert new expense head
            record = {
                **head,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": "System Seed"
            }
            await db.expense_heads.insert_one(record)
            inserted += 1
            print(f"  Inserted: {head['name']}")
        
        final_count = await db.expense_heads.count_documents({})
        print(f"\nSeed complete!")
        print(f"  Inserted: {inserted}")
        print(f"  Skipped (already exist): {skipped}")
        print(f"  Total expense heads: {final_count}")
        
        return True
        
    except Exception as e:
        print(f"ERROR during seeding: {e}")
        return False
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed_expense_heads())
