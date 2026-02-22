# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, and Recipe Admin panel for MGT.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Feb 22, 2026)
- ✅ **OTP Email System** - Using EXACT method from original server.py
  - Uses `config.json` for email settings (same as original)
  - Uses `EmailMessage` class (same as original)
  - Falls back to console logging when SMTP not configured
  
- ✅ **Bhojan Guru with PDF Recipes** - 41 recipes from "Purnabramha Recipe all - final 16112021.pdf"
  - Masala Buttermilk, Plain Buttermilk, Solkadhi, Masala Kokam, Kokam
  - Piyush, Rose Piyush, Mango Piyush, Awala, Aam Panha
  - Limbu Pani, Masala Lemon, Tea & Masala Tea
  - Kanda Bhaji, Appa Pakoda, Kothimbir Vadi, Kachori, Batata Vada
  - Kandapohe, Dadpe Pohe, Ghavan, Mix Dal Vada, Moong Dal Pakoda
  - Palak Pakoda, Kadhi, Varans (Jeera, Methi, Palak, Chincha Gulacha)
  - Chutneys (Green, Tamarind, Vada Pav)
  - Fasting items (Sabudana Khichdi, Sabudana Vada)
  - Sweets (Shrikhand, Gulab Jamun, Aliv Kheer, Nachani Chi Kheer, Puran Poli, Modak)

- ✅ **ResizeObserver Error Fixed** - No more error overlay on dropdown clicks

- ✅ **Recipe Admin Panel (MGT Only)** - Full CRUD for recipes
  - Create, Edit, Delete recipes
  - Search and filter by category

- ✅ **Guest Response AI with Center Selector**

## How to Enable OTP Email

Edit `/app/backend/config.json`:
```json
{
    "otp": {"length": 6, "ttl_seconds": 300},
    "security": {"session_ttl_seconds": 43200},
    "email": {
        "enabled": true,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "YOUR_EMAIL@gmail.com",
        "smtp_pass": "YOUR_APP_PASSWORD",
        "from_name": "Purnabramha Attendance",
        "from_email": "YOUR_EMAIL@gmail.com"
    }
}
```

For Gmail, create an App Password at: https://myaccount.google.com/apppasswords

## Centers & Managers
| Center | Manager | Mobile | Email |
|--------|---------|--------|-------|
| PB-MGT | Jayanti Kathale | 9741399190 | (from Managers worksheet) |
| PB-MGT | Sandeep Gadhwal | 9960886185 | (from Managers worksheet) |

## Key Files
- `/app/backend/config.json` - Email configuration (same as original server.py)
- `/app/backend/recipe_data.json` - 41 recipes from PDF
- `/app/backend/description_data.json` - 126 menu descriptions
- `/app/frontend/src/pages/BhojanGuru.jsx` - Recipe display
- `/app/frontend/src/pages/RecipeAdmin.jsx` - Recipe management
- `/app/frontend/src/pages/GuestResponse.jsx` - AI chat with center selector

## Dev Mode
- Master OTP: 123456 (works for testing)
- OTP logged to console when email not configured

## Testing
- Backend: All APIs working
- Frontend: All pages functional
- Recipe CRUD: Tested and working
