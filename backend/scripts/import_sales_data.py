#!/usr/bin/env python3
"""
Excel Data Import Script for Sales & Expenses
Imports data from Purnabramha Excel files into MongoDB
"""

import asyncio
import os
import sys
import urllib.request
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import load_workbook
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Center mapping from filename to center code
CENTER_MAP = {
    "DOMBIVALI": "PB-DV",
    "HINJEWADI PUNE": "PB-HW",
    "HINJEWADI": "PB-HW",
    "HSR": "PB-HSR",
    "KALYAN": "PB-KAL",
    "KHARADINYATI": "PB-KN",
    "KHARADI": "PB-KN",
    "SN": "PB-SN",
    "THANE": "PB-TH",
    "PERTH": "PB-PT"
}

# Excel file URLs
EXCEL_FILES = [
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/cgddwzmo_DOMBIVALI-DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-DV",
        "name": "DOMBIVALI"
    },
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/e0djcl8w_HINJEWADI%20PUNE-DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-HW",
        "name": "HINJEWADI PUNE"
    },
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/ybmgtmyq_HSR%20-DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-HSR",
        "name": "HSR"
    },
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/d8jyi1ha_KALYAN-DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-KAL",
        "name": "KALYAN"
    },
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/4m429xk2_KHARADINYATI%20-%20DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-KN",
        "name": "KHARADINYATI"
    },
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/28od7h1x_SN%20-%20DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-SN",
        "name": "SN"
    },
    {
        "url": "https://customer-assets.emergentagent.com/job_4ad52ebb-f6da-4ddb-8bf9-3fc6171c0a7c/artifacts/hix8svvl_THANE-DAILY-SALE%20N%20CASH%20SUMMERY%202025-2026.xlsx",
        "center": "PB-TH",
        "name": "THANE"
    }
]

def safe_float(value, default=0):
    """Safely convert value to float"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            # Remove commas and other formatting
            cleaned = value.replace(',', '').replace('₹', '').strip()
            if not cleaned or cleaned in ['#REF!', '#VALUE!', '-', 'NA', 'N/A']:
                return default
            return float(cleaned)
        except:
            return default
    return default

def parse_date(value):
    """Parse date from various formats"""
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    
    if isinstance(value, str):
        # Try various formats
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y', '%d-%m-%Y', '%Y/%m/%d']
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt).strftime('%Y-%m-%d')
            except:
                continue
    return None

def find_main_sheet(wb):
    """Find the main daily sales summary sheet"""
    # Look for the main sheet - usually "DAILY SALE N CASH SUMMERY" or "Sheet1"
    for name in wb.sheetnames:
        name_upper = name.upper()
        if 'DAILY SALE' in name_upper or 'CASH SUMM' in name_upper:
            return wb[name]
    
    # Try first sheet if it has the right structure
    first_sheet = wb[wb.sheetnames[0]]
    cell_a1 = first_sheet.cell(row=1, column=1).value
    if cell_a1 and 'DATE' in str(cell_a1).upper():
        return first_sheet
    
    # Look for a sheet with proper columns
    for name in wb.sheetnames:
        sheet = wb[name]
        cell_a1 = sheet.cell(row=1, column=1).value
        if cell_a1 and 'DATE' in str(cell_a1).upper():
            return sheet
    
    return wb.active

def find_expense_sheets(wb):
    """Find monthly expense sheets"""
    expense_sheets = []
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    
    for name in wb.sheetnames:
        name_upper = name.upper()
        # Look for month sheets like "APR 25", "MAY 25", etc.
        for month in months:
            if month in name_upper and ('25' in name or '26' in name or '24' in name):
                # Verify it has expense structure
                sheet = wb[name]
                headers = []
                for col in range(1, min(10, sheet.max_column + 1)):
                    h = sheet.cell(row=1, column=col).value
                    if h:
                        headers.append(str(h).upper())
                
                if any('DATE' in h for h in headers) and any('AMOUNT' in h or 'EXPENCE' in h or 'EXPENSE' in h for h in headers):
                    expense_sheets.append({
                        'name': name,
                        'sheet': sheet,
                        'month': month
                    })
                break
    
    return expense_sheets

async def import_daily_sales(db, file_info):
    """Import daily sales data from Excel file"""
    logger.info(f"Processing {file_info['name']}...")
    
    # Download file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        try:
            urllib.request.urlretrieve(file_info['url'], tmp.name)
            wb = load_workbook(tmp.name, data_only=True)  # data_only=True to get calculated values
        except Exception as e:
            logger.error(f"Failed to download/open {file_info['name']}: {e}")
            return 0, 0
        
        # Find main sales sheet
        sheet = find_main_sheet(wb)
        logger.info(f"Using sheet: {sheet.title}")
        
        # Determine column mapping based on headers
        # Standard mapping from HSR file analysis
        col_map = {
            'date': 1,
            'opening_balance': 2,
            'deposited_in_bank': 3,
            'petty_cash_opening': 4,
            'cash_receipts': 5,
            'sale_pbm': 6,  # Column F - PBM
            'sale_other': 7,  # Column G - Other products (if exists)
            'total_sale': 9,  # Column I - Total sale of the day (sometimes calculated)
            'card_idfc': 10,
            'bharat_pay': 11,
            'swiggy': 12,
            'zomato': 13,
            'online_other': 14,
            'due_amount': 15,
            'total_online_sale': 16,
            'total_cash_sale': 17,
            'cash_expense': 18,
            'closing_balance': 19,
            'to_deposit_in_bank': 21,
            'difference_for_day': 22,
            'petty_cash_closing': 23
        }
        
        center = file_info['center']
        sales_count = 0
        skip_count = 0
        
        # Start from row 4 (row 1-2 are headers, row 3 is often blank)
        for row_num in range(4, min(sheet.max_row + 1, 400)):  # Limit to 400 rows for safety
            try:
                date_val = sheet.cell(row=row_num, column=col_map['date']).value
                date_str = parse_date(date_val)
                
                if not date_str:
                    continue
                
                # Skip if year is not 2025 or 2026
                year = int(date_str.split('-')[0])
                if year < 2024:
                    continue
                
                # Get values
                record = {
                    'center': center,
                    'date': date_str,
                    'opening_balance': safe_float(sheet.cell(row=row_num, column=col_map['opening_balance']).value),
                    'petty_cash_opening': safe_float(sheet.cell(row=row_num, column=col_map['petty_cash_opening']).value),
                    'deposited_in_bank': safe_float(sheet.cell(row=row_num, column=col_map['deposited_in_bank']).value),
                    'cash_receipts': safe_float(sheet.cell(row=row_num, column=col_map['cash_receipts']).value),
                    'sale_pbm': safe_float(sheet.cell(row=row_num, column=col_map['sale_pbm']).value),
                    'sale_other': safe_float(sheet.cell(row=row_num, column=col_map.get('sale_other', 7)).value),
                    'card_idfc': safe_float(sheet.cell(row=row_num, column=col_map['card_idfc']).value),
                    'bharat_pay': safe_float(sheet.cell(row=row_num, column=col_map['bharat_pay']).value),
                    'swiggy': safe_float(sheet.cell(row=row_num, column=col_map['swiggy']).value),
                    'zomato': safe_float(sheet.cell(row=row_num, column=col_map['zomato']).value),
                    'online_other': safe_float(sheet.cell(row=row_num, column=col_map['online_other']).value),
                    'due_amount': safe_float(sheet.cell(row=row_num, column=col_map['due_amount']).value),
                    'cash_expense': safe_float(sheet.cell(row=row_num, column=col_map['cash_expense']).value),
                    'created_at': datetime.utcnow().isoformat(),
                    'created_by': 'Excel Import'
                }
                
                # Calculate totals
                record['total_sale'] = record['sale_pbm'] + record['sale_other']
                record['total_online_sale'] = (
                    record['card_idfc'] + 
                    record['bharat_pay'] + 
                    record['swiggy'] + 
                    record['zomato'] + 
                    record['online_other']
                )
                record['total_cash_sale'] = record['total_sale'] - record['total_online_sale']
                
                # Calculate closing balance
                record['closing_balance'] = (
                    record['opening_balance'] + 
                    record['total_cash_sale'] + 
                    record['cash_receipts'] - 
                    record['deposited_in_bank'] - 
                    record['cash_expense']
                )
                
                record['petty_cash_closing'] = (
                    record['petty_cash_opening'] + 
                    record['cash_receipts'] - 
                    record['cash_expense']
                )
                
                record['to_deposit_in_bank'] = record['closing_balance'] - record['petty_cash_closing']
                record['difference_for_day'] = 0  # Will be calculated based on actual vs expected
                
                # Skip if total sale is 0 (likely empty row)
                if record['total_sale'] == 0 and record['cash_expense'] == 0:
                    skip_count += 1
                    continue
                
                # Upsert into database
                await db.daily_sales.update_one(
                    {'center': center, 'date': date_str},
                    {'$set': record},
                    upsert=True
                )
                sales_count += 1
                
            except Exception as e:
                logger.warning(f"Error processing row {row_num}: {e}")
                continue
        
        # Import expenses from monthly sheets
        expense_sheets = find_expense_sheets(wb)
        expense_count = 0
        
        for exp_sheet_info in expense_sheets:
            exp_sheet = exp_sheet_info['sheet']
            logger.info(f"Processing expense sheet: {exp_sheet_info['name']}")
            
            # Find column indices for expense sheet
            exp_col_map = {'date': 1, 'description': 2, 'amount': 3, 'expense_type': 4, 'payment_mode': 5}
            
            # Check headers
            for col in range(1, min(10, exp_sheet.max_column + 1)):
                h = exp_sheet.cell(row=1, column=col).value
                if h:
                    h_upper = str(h).upper()
                    if 'DATE' in h_upper:
                        exp_col_map['date'] = col
                    elif 'EXPENCE' in h_upper or 'EXPENSE' in h_upper:
                        exp_col_map['description'] = col
                    elif 'AMOUNT' in h_upper:
                        exp_col_map['amount'] = col
                    elif 'TYPE' in h_upper:
                        exp_col_map['expense_type'] = col
                    elif 'MODE' in h_upper or 'CASH' in h_upper:
                        exp_col_map['payment_mode'] = col
            
            for row_num in range(2, min(exp_sheet.max_row + 1, 500)):
                try:
                    date_val = exp_sheet.cell(row=row_num, column=exp_col_map['date']).value
                    date_str = parse_date(date_val)
                    
                    if not date_str:
                        continue
                    
                    description = exp_sheet.cell(row=row_num, column=exp_col_map['description']).value
                    amount = safe_float(exp_sheet.cell(row=row_num, column=exp_col_map['amount']).value)
                    expense_type = exp_sheet.cell(row=row_num, column=exp_col_map['expense_type']).value
                    payment_mode = exp_sheet.cell(row=row_num, column=exp_col_map.get('payment_mode', 5)).value
                    
                    if not description or amount == 0:
                        continue
                    
                    exp_record = {
                        'center': center,
                        'date': date_str,
                        'description': str(description)[:200] if description else '',
                        'amount': amount,
                        'expense_type': str(expense_type).upper() if expense_type else 'OTHER',
                        'payment_mode': str(payment_mode).upper() if payment_mode else 'CASH',
                        'created_at': datetime.utcnow().isoformat(),
                        'created_by': 'Excel Import'
                    }
                    
                    await db.expenses.insert_one(exp_record)
                    expense_count += 1
                    
                except Exception as e:
                    continue
        
        logger.info(f"Imported {sales_count} daily sales, {expense_count} expenses for {center}")
        
        # Cleanup
        os.unlink(tmp.name)
        
        return sales_count, expense_count

async def main():
    """Main import function"""
    logger.info("Starting Excel data import...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Clear existing data (optional - comment out if you want to preserve)
    logger.info("Clearing existing sales and expenses data...")
    await db.daily_sales.delete_many({})
    await db.expenses.delete_many({})
    
    # Create indexes
    await db.daily_sales.create_index([("center", 1), ("date", 1)], unique=True)
    await db.expenses.create_index([("center", 1), ("date", 1)])
    await db.expenses.create_index([("expense_type", 1)])
    
    total_sales = 0
    total_expenses = 0
    
    for file_info in EXCEL_FILES:
        try:
            sales, expenses = await import_daily_sales(db, file_info)
            total_sales += sales
            total_expenses += expenses
        except Exception as e:
            logger.error(f"Failed to process {file_info['name']}: {e}")
    
    logger.info(f"\n=== Import Complete ===")
    logger.info(f"Total daily sales records: {total_sales}")
    logger.info(f"Total expense records: {total_expenses}")
    
    # Print summary by center
    logger.info("\n=== Sales by Center ===")
    pipeline = [
        {"$group": {"_id": "$center", "count": {"$sum": 1}, "total_sale": {"$sum": "$total_sale"}}}
    ]
    async for doc in db.daily_sales.aggregate(pipeline):
        logger.info(f"  {doc['_id']}: {doc['count']} records, Total: ₹{doc['total_sale']:,.2f}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
