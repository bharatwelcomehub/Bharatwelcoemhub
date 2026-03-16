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
- **Architecture**: SPA with RESTful API + Database-driven Menu

## ✅ Completed Features

### Phase 1-6 - Core App (Previous Sessions)
- [x] Full-stack app scaffolding
- [x] Dual currency menu system (INR/AUD)
- [x] Customer authentication (Email/Password + Google OAuth)
- [x] PWA support

### Phase 7 - Production Feature Rebuild (March 2026)
- [x] **Data-Driven Architecture** - JSON config files for centers, booking rules, catering packages, tiffin config
- [x] **Table Booking** (`/table-booking`) - Full multi-step form with WhatsApp
- [x] **Tiffin Booking** (`/tiffin`) - Weekly lunch boxes + Unlimited Breakfast (₹299/person)
- [x] **Pickup Orders** (`/pickup`) - E-commerce style with cart
- [x] **Catering Booking** (`/catering`) - 4 packages with menu selection

### Phase 8 - Admin & Homepage Enhancement (March 2026)
- [x] **Admin Panel Menu Management**
  - Full CRUD for menu items (name, description, category, prices INR/AUD, image, availability)
  - 173+ menu items in database
  - Changes reflect instantly across all features (Pickup, Table Booking, etc.)
  - Banner/Hero image management
  - Location management
  - Video management

- [x] **Modern Luxe Homepage Redesign**
  - Full-screen hero with parallax background
  - "Book a Table" and "Order Pickup" prominent CTAs
  - Stats: 8+ Locations, 50K+ Happy Customers, 150+ Menu Items, 4.8 Rating
  - Services section with animated cards (Dine In, Pickup, Tiffin, Catering)
  - Featured Dishes carousel with pricing
  - Unlimited Breakfast Buffet offer banner
  - Auto-rotating testimonials with star ratings
  - Locations grid with phone numbers
  - Final CTA section with multiple options

- [x] **Database-Frontend Integration**
  - Pickup page fetches menu from `/api/menu` endpoint
  - Fallback to JSON config if database empty
  - Regional pricing: India → ₹, Australia → $

## 📋 Backlog Tasks

### P1 - High Priority
- [ ] Payment Integration (Razorpay for India, Stripe for Perth) - *User deferred*
- [ ] Make Table Booking and Catering also fetch from database

### P2 - Medium Priority
- [ ] Location-based automatic pricing (geo-detection)
- [ ] Video/Reels page functionality
- [ ] Push notifications (Firebase)

### P3 - Future
- [ ] Customer order history
- [ ] Loyalty/rewards program

## API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/menu | GET | Get available menu items |
| /api/locations | GET | Get active locations |
| /api/hero-image | GET | Get active homepage banner |
| /api/admin/menu | GET/POST/PUT/DELETE | Admin menu management |
| /api/admin/locations | GET/POST/PUT | Admin location management |
| /api/admin/hero-images | GET/POST/PUT/DELETE | Admin banner management |
| /api/admin/videos | POST/DELETE | Admin video management |

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
- `/app/frontend/src/pages/Home.js` - New Modern Luxe homepage
- `/app/frontend/src/pages/Admin.js` - Admin dashboard with menu CRUD
- `/app/frontend/src/pages/Pickup.js` - Pickup orders with DB integration
- `/app/frontend/src/pages/TableBooking.js` - Table booking
- `/app/frontend/src/pages/Tiffin.js` - Tiffin & breakfast
- `/app/frontend/src/pages/Catering.js` - Catering inquiry
- `/app/frontend/src/config/*.json` - Business configuration

## Test Reports
- `/app/test_reports/iteration_3.json` - Latest (100% pass, 17/17 backend tests)
