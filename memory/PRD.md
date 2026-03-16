# Purnabramha Restaurant App - Product Requirements Document

## Original Problem Statement
The owner of "Purnabramha" restaurant chain wants to convert their website (www.purnabramha.com) into a full-fledged application with:
- Pickup ordering functionality
- Admin dashboard with full control
- Menu management with location-based pricing (India ₹ and Australia $)
- Video content sections (Reels and Inspiration)
- Franchise inquiry page
- Location-specific Google Reviews
- Catering booking system

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Framer Motion
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Architecture**: Single Page Application (SPA) with RESTful API

## Database Schema
```
menu_items: { id, name, description, category, price_inr, price_aud, image_url, is_veg, is_available }
locations: { id, name, city, country, address, phone, whatsapp, google_review_link, is_active }
users: { id, email, password, name, phone, role: ['admin', 'customer'], created_at }
videos: { id, title, video_url, thumbnail_url, description, category, is_active, created_at }
```

## ✅ Completed Features

### Phase 1 - Core App Structure (Completed Dec 2025)
- [x] Full-stack app scaffolding (React/FastAPI/MongoDB)
- [x] Created pages: Home, Menu, Tiffin, Locations, Franchise, About
- [x] Franchise page with contact: 9741399190
- [x] Locations page with Google Review links

### Phase 2 - Menu & Pricing (Completed Feb 2026)
- [x] **Menu Data Extraction**: Extracted 173 menu items from PDF menus (India & Australia)
- [x] **Dual Currency Pricing**: Menu supports both INR (₹) and AUD ($) pricing
- [x] **Country Selector**: Toggle between India and Australia on Menu page
- [x] **Menu Categories**: 16 categories including Kids, Snacks, Heavy Brunch, Special Thalis, etc.
- [x] **Database Seeding**: Created comprehensive seed script with all menu items

### Phase 3 - Table Booking & Tiffin Service (Completed Feb 2026)
- [x] **Table Booking Page**: Complete booking form with all 8 centers (India & Australia)
- [x] **Dine-In / Pickup Selection**: Service type selection for each booking
- [x] **Time Slots**: 6 time slots (12PM-10PM range)
- [x] **Celebration Options**: Birthday, Anniversary, Gudi Padwa, Fasting, etc.
- [x] **WhatsApp Integration**: Sends booking request directly to center WhatsApp
- [x] **Tiffin Service Page**: Weekly lunch box subscription system
- [x] **Heavy Brunch Add-ons**: Daily brunch items with drink add-ons
- [x] **Week Selection**: 3-week advance booking with Mon-Fri options
- [x] **Pricing by Center**: Different pricing for India (₹) vs Australia ($)
- [x] **Order Summary**: Real-time calculation of totals

### Phase 4 - Admin Dashboard (Completed Feb 2026)
- [x] **Admin Login**: Secure authentication (admin@purnabramha.com / admin123)
- [x] **Home Banner Management**: Add, edit, set active banner for homepage
- [x] **Menu Management**: Add, edit, delete menu items with INR/AUD pricing
- [x] **Location Management**: View and edit 8 restaurant locations
- [x] **Video Management**: Add and delete video content
- [x] **Dashboard Tabs**: Home Banner, Menu (173), Locations (8), Videos

### Phase 5 - PWA Support (Completed Feb 2026)
- [x] **Progressive Web App**: App can be installed on mobile devices
- [x] **Manifest.json**: App name, icons, theme colors configured
- [x] **Service Worker**: Offline caching support
- [x] **Install Prompt**: Shows users how to add app to home screen
- [x] **iOS Support**: Safari "Add to Home Screen" instructions

### Phase 6 - Customer Authentication (Completed Feb 2026)
- [x] **Email/Password Login**: Traditional login with email and password
- [x] **Email/Password Registration**: Sign up with name, email, phone, password
- [x] **Google OAuth Login**: One-click sign in with Google (Emergent Auth)
- [x] **Session Management**: JWT tokens and cookie-based sessions
- [x] **Auth Callback**: Handles Google OAuth redirect
- [x] **Push Notification Structure**: Basic endpoints ready for Firebase integration (0)

### Bug Fixes (Feb 2026)
- [x] Fixed navigation spacing issue - menu items now properly spaced
- [x] Fixed menu data - replaced scraped data with accurate PDF data

## 🔄 In Progress
- [ ] Catering Page Logic - needs re-implementation from catering.html

## 📋 Upcoming Tasks (P1)
- [ ] Location-based automatic pricing (geo-detection)
- [ ] Implement Video/Reels page functionality
- [ ] Implement Inspiration page (Jayanti Kathale videos)

## 📋 Future Tasks (P2/P3)
- [ ] Payment Integration (Razorpay for India, Stripe for Australia)
- [ ] Customer Authentication (login/signup for orders)
- [ ] Order Management System
- [ ] Tiffin Subscription Management
- [ ] Table Booking Enhancement

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/menu | GET | Get all menu items |
| /api/locations | GET | Get active locations |
| /api/videos | GET | Get videos by category |
| /api/auth/login | POST | User login |
| /api/auth/register | POST | User registration |
| /api/admin/menu | GET/POST | Admin menu management |
| /api/admin/menu/{id} | PUT/DELETE | Update/delete menu item |
| /api/admin/locations | GET/POST | Admin location management |
| /api/admin/videos | POST | Add video |
| /api/admin/videos/{id} | DELETE | Delete video |

## Admin Credentials
- **Email**: admin@purnabramha.com
- **Password**: admin123
- **Admin URL**: https://purnabramha-app-2.preview.emergentagent.com/admin

## Key Files
- `/app/backend/server.py` - All API endpoints
- `/app/backend/seed_menu_data.py` - Database seed script
- `/app/frontend/src/pages/Menu.js` - Menu with country selector
- `/app/frontend/src/pages/Admin.js` - Admin dashboard
- `/app/frontend/src/contexts/AuthContext.js` - Authentication
