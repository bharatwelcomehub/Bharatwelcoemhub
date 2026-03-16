# Purnabramha Restaurant App - Product Requirements Document

## Original Problem Statement
The owner of "Purnabramha" restaurant chain wants a full-fledged, production-ready web application for `app.purnabramha.com` with:
- Pickup ordering functionality
- Table booking system
- Tiffin/lunch box subscriptions
- Catering inquiry system
- Admin dashboard with full control
- Menu management with location-based pricing (India ₹ and Australia $)

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Framer Motion
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Architecture**: SPA with RESTful API + JSON Config-Driven Frontend

## Database Schema
```
menu_items: { id, name, description, category, price_inr, price_aud, image_url, is_veg, is_available }
locations: { id, name, city, country, address, phone, whatsapp, google_review_link, is_active }
users: { id, email, password, name, phone, role: ['admin', 'customer'], created_at }
videos: { id, title, video_url, thumbnail_url, description, category, is_active, created_at }
heroimages: { title, description, image_url, is_active }
admins: { email, password_hash }
```

## ✅ Completed Features

### Phase 1-6 - Core App, Menu, Auth, PWA (Previous Sessions)
- [x] Full-stack app scaffolding (React/FastAPI/MongoDB)
- [x] Created pages: Home, Menu, Locations, Franchise, About, Videos, Inspiration
- [x] Dual currency menu system (INR/AUD)
- [x] Admin dashboard with CRUD for menus, locations, videos, banners
- [x] Customer authentication (Email/Password + Google OAuth)
- [x] PWA support with install prompts

### Phase 7 - Production Feature Rebuild (March 2026)
- [x] **Data-Driven Architecture**: Created JSON config files for all business logic
  - `centers.json` - 8 locations (7 India + 1 Perth) with WhatsApp numbers
  - `menus-india.json` - Full menu with INR pricing (173+ items)
  - `menus-perth.json` - Full menu with AUD pricing
  - `booking-rules.json` - Time slots, celebration types, disclaimers
  - `catering-packages.json` - 4 packages with India/Australia pricing
  - `tiffin-config.json` - Lunch box, heavy brunch, unlimited breakfast

- [x] **Feature 1: Table Booking** (`/table-booking`)
  - Region/Center selection (India 🇮🇳 / Australia 🇦🇺)
  - Date picker with 2-hour advance, 30-day max
  - 6 time slots (12PM-10PM)
  - Service type (Dine-In / Pickup)
  - Guest details with celebration options
  - Menu pre-ordering for Perth/Pickup
  - WhatsApp message generation with order summary

- [x] **Feature 2: Tiffin Booking** (`/tiffin`)
  - Weekly lunch box subscriptions (Mon-Fri)
  - 3 lunch box options per region
  - Heavy Brunch items with Buttermilk/Kokum addons
  - **Unlimited Breakfast** (₹299 India / $35 Perth per person)
  - Perth blackout dates (Dec 15 - Jan 10)
  - GST calculation for India (5%)
  - Live order summary with totals

- [x] **Feature 3: Pickup Orders** (`/pickup`)
  - E-commerce style menu browsing
  - Category tabs with search
  - Real-time cart management
  - Minimum order validation (₹200 India / $20 Australia)
  - WhatsApp order submission

- [x] **Feature 4: Catering Booking** (`/catering`)
  - Event details form with Google Maps link
  - 4 catering packages:
    - Classic: ₹450/$35 per person
    - Premium: ₹600/$45 per person
    - Special Feast: ₹750/$55 per person
    - Royal Feast: ₹950/$70 per person (Most Popular)
  - Menu selection based on package requirements
  - Min 20 guests, 7+ days advance booking
  - Estimated total calculation

## 📋 Backlog Tasks

### P1 - High Priority
- [ ] Payment Integration (Razorpay for India, Stripe for Perth) - *User deferred*
- [ ] Location-based automatic pricing (geo-detection)

### P2 - Medium Priority
- [ ] Video/Reels page functionality
- [ ] Push notifications (Firebase)
- [ ] Order management system

### P3 - Future
- [ ] Customer order history
- [ ] Loyalty/rewards program

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/menu | GET | Get all menu items |
| /api/locations | GET | Get active locations |
| /api/videos | GET | Get videos by category |
| /api/auth/login | POST | User login |
| /api/auth/register | POST | User registration |
| /api/admin/menu | GET/POST | Admin menu management |
| /api/admin/locations | GET/POST | Admin location management |

## Admin Credentials
- **Email**: admin@purnabramha.com
- **Password**: admin123

## Center WhatsApp Numbers
| Center | WhatsApp |
|--------|----------|
| HSR Bangalore | +91 85500 78515 |
| Ch. Sambhajinagar | +91 89710 49084 |
| Thane Mumbai | +91 89047 49084 |
| Dombivli Mumbai | +91 96064 55433 |
| Kharadi Pune | 9900089803 |
| Hinjawadi Pune | 9606455434 |
| Kalyan Mumbai | 8792887442 |
| Perth Australia | +61 401 832 922 |

## Key Files
- `/app/backend/server.py` - All API endpoints
- `/app/frontend/src/pages/TableBooking.js` - Table booking feature
- `/app/frontend/src/pages/Tiffin.js` - Tiffin & breakfast booking
- `/app/frontend/src/pages/Pickup.js` - Pickup orders
- `/app/frontend/src/pages/Catering.js` - Catering inquiry
- `/app/frontend/src/config/*.json` - All business configuration

## Test Reports
- `/app/test_reports/iteration_2.json` - Latest test results (100% pass)
