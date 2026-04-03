# Purnabramha Restaurant App - Product Requirements Document

## Original Problem Statement
Full-fledged, production-ready web application for `app.purnabramha.com` with pickup ordering, table booking, tiffin subscriptions, catering services, and admin dashboard.

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Framer Motion
- **Backend**: FastAPI (Python)
- **Database**: MongoDB

## Admin Credentials
- **Email**: PBadmin@purnabramha.com
- **Password**: PB22052012

## Completed Features

### Core Features
- [x] Full-stack app with React + FastAPI + MongoDB
- [x] Dual currency menu (INR / AUD)
- [x] Customer authentication (Email/Password + Google OAuth)
- [x] PWA support for mobile install

### SEO Optimization (NEW)
- [x] **Dynamic Meta Tags** - Title, description, keywords with city name
- [x] **OpenGraph Tags** - For social sharing (Facebook, Twitter)
- [x] **Location Detection** - Ask permission popup, find nearest center
- [x] **Dynamic H1/H2** - "Authentic Maharashtrian Food in {City}"
- [x] **JSON-LD Schema** - Organization, Restaurant, FAQ structured data
- [x] **FAQ Section** - SEO-optimized footer with 3 Q&As
- [x] **Internal City Links** - Perth, Pune, Thane, Kalyan, Bangalore, Dombivli
- [x] **"Near Me" Banner** - Top banner with location permission button
- [x] **sitemap.xml** - All pages indexed
- [x] **robots.txt** - Search engine crawl rules
- [x] **Canonical URLs** - Prevent duplicate content

### Admin Panel (`/admin`)
- [x] **Home Banner** - Manage hero images
- [x] **Festivals** - 12-month festival theme management with:
  - Gudhi Padwa/Ugadi (March 21) - Maharashtra New Year
  - Makar Sankranti, Maha Shivaratri, Hanuman Jayanti, etc.
  - Custom colors (primary, secondary, accent)
  - Marathi greetings
  - One-click activate/deactivate
- [x] **Menu CRUD** (173+ items) - name, description, category, prices, images
- [x] **Dietary Tags** - No Onion/Garlic and Fasting Friendly boolean flags with bold colored badges
  - Admin: Checkboxes in Add/Edit Menu Item dialog
  - Menu Page: Orange 'No Onion/Garlic' and purple 'Fasting Friendly' badges on cards and modal
  - Pickup Page: Dietary badges on MenuItemCard
- [x] **AI Nutrition & Health Analysis** (Apr 2026) - Click any dish to see full nutrition profile
  - Calories, Protein, Carbs, Fats, Fiber with visual macro split bar
  - Health Benefits (4 bullet points per dish)
  - Ayurvedic/Maharashtrian traditional wisdom
  - Allergen warnings (Peanuts, Dairy, etc.)
  - Dietary tags (Gluten Free, High Protein, etc.)
  - AI-generated via GPT, cached in MongoDB for instant loading
  - Admin "Generate Nutrition AI" button for bulk generation
  - Works for both India and Australia menus
- [x] **Scan Dish (AI Image Recognition)** (Apr 2026) - Take photo or upload image of any dish
  - Floating camera button on Menu page
  - AI identifies dish from menu using GPT-4.1 vision
  - Shows matched dish with full nutrition card + "Order for Pickup" button
  - Supports camera capture (mobile) and gallery upload
  - Handles unidentified dishes gracefully with retry option
- [x] **Bulk Image Upload** - Paste Google Drive URLs for items without images
- [x] **Tiffin Management** - Full CRUD with:
  - Unlimited Breakfast Settings (price, description, timings, days)
  - Lunch Box Options management
  - Heavy Brunch Items management
  - Drink Add-ons management
  - Add/Edit/Delete tiffin items with dialog
- [x] **Locations** (8 centers) - Full CRUD
- [x] **Videos** - Video/reels management

### Festival Theme Feature (NEW)
- [x] Pre-configured 12 Maharashtrian/Indian festivals
- [x] Automatic festival banner on homepage when active
- [x] Customizable colors, greetings, and banner images
- [x] Admin can activate any month's festival theme
- [x] Festival greeting in Marathi (e.g., "गुढीपाडव्याच्या हार्दिक शुभेच्छा!")

### Modern Luxe Homepage
- [x] Full-screen hero with authentic Purnabramha food photos
- [x] **Festival Banner** - Shows active festival theme at top
- [x] Stats: 8+ Locations, 50K+ Customers, 150+ Items
- [x] 4 Service cards (Dine In, Pickup, Tiffin, Catering)
- [x] Featured dishes carousel with your photos
- [x] Unlimited Breakfast offer banner
- [x] Testimonials slider
- [x] Locations grid

### Table Booking (`/table-booking`)
- [x] Region/Center selection (India/Australia)
- [x] Date picker (min 2hr advance, max 30 days)
- [x] Time slots (12PM-10PM)
- [x] Guest details + celebration type
- [x] Menu pre-ordering for Perth
- [x] WhatsApp confirmation

### Tiffin Booking (`/tiffin`)
- [x] Weekly lunch box subscriptions
- [x] Heavy brunch with drink add-ons
- [x] **Unlimited Breakfast**: 299 INR (India) / $35 (Perth)
- [x] Perth blackout dates (Dec 15 - Jan 10)
- [x] GST calculation for India (5%)

### Pickup Orders (`/pickup`)
- [x] **Pickup Date field** (today onwards, max 30 days)
- [x] Pickup Time selection
- [x] Menu from database with fallback to JSON
- [x] Category tabs + search
- [x] Cart management
- [x] Minimum order validation (200 INR / $20)

### Catering Booking (`/catering`)
- [x] 4 Packages: Classic (450), Premium (600), Special (750), Royal Feast (950)
- [x] Menu selection per package requirements
- [x] Google Maps link generation
- [x] **Addon Services**
  - Crockery & Cutlery Rental: 3,000/hr (India) / $200/hr (Perth)
  - Service Staff: 300/person/hr (India) / $50/person/hr (Perth)

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

## Your Google Drive Images (In Use)
- Hero: `1IiJw4VxwbygR2WXSymVgd9S7FoIfrdil`
- Kaju Curry: `1rYkehXEPrE9I4jf1QnaICJscFd3Vso2v`
- Bharit: `1RwL7pG0gZa6VlRY_hdPJAUfXNKCezU2V`
- Maswadi: `168pHmUxU4vyqA4DrplT0_9R_DDK9eK0c`
- Patodi: `1VYDK8vRc_hVR4jn1CsabdBL0fFF4EWaH`

URL format: `https://lh3.googleusercontent.com/d/FILE_ID`

## API Endpoints

### Public
- `GET /api/festival-theme` - Get active festival theme
- `GET /api/hero-image` - Get active homepage banner
- `GET /api/menu` - Get menu items
- `GET /api/locations` - Get all locations
- `GET /api/tiffin-items` - Get tiffin menu items
- `GET /api/tiffin-config` - Get unlimited breakfast config

### Admin
- `GET/POST/PUT/DELETE /api/admin/festival-themes` - Festival CRUD
- `GET/POST/PUT/DELETE /api/admin/menu` - Menu CRUD
- `GET/POST/PUT/DELETE /api/admin/tiffin-items` - Tiffin items CRUD
- `PUT /api/admin/tiffin-config` - Update breakfast config
- `GET/POST/PUT/DELETE /api/admin/hero-images` - Banner CRUD
- `GET/POST/PUT /api/admin/locations` - Location CRUD

## Backlog
- [ ] Tiffin Page Migration - Refactor Tiffin.js to use database APIs instead of hardcoded JSON
- [ ] Payment Integration (Razorpay/Stripe)
- [ ] Push notifications
- [ ] Order history dashboard
- [ ] Multi-language support

## Bug Fixes
- [x] Catering page: Desserts, Drinks, Sides selection was blocked ("Maximum 0 allowed") due to singular/plural key mismatch between package requirements JSON and frontend category keys (Apr 2026)
