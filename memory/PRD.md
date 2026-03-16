# Purnabramha Restaurant App - Product Requirements Document

## Original Problem Statement
Full-fledged, production-ready web application for `app.purnabramha.com` with pickup ordering, table booking, tiffin subscriptions, catering services, and admin dashboard.

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn UI, Framer Motion
- **Backend**: FastAPI (Python)
- **Database**: MongoDB

## ✅ Completed Features

### Core Features
- [x] Full-stack app with React + FastAPI + MongoDB
- [x] Dual currency menu (₹ INR / $ AUD)
- [x] Customer authentication (Email/Password + Google OAuth)
- [x] PWA support for mobile install

### Admin Panel (`/admin`)
- [x] Menu CRUD (name, description, category, prices, images, availability)
- [x] Home banner management
- [x] Location management
- [x] Video management
- **Login**: admin@purnabramha.com / admin123

### Modern Luxe Homepage
- [x] Full-screen hero with authentic Purnabramha food photos
- [x] Stats: 8+ Locations, 50K+ Customers, 150+ Items
- [x] 4 Service cards (Dine In, Pickup, Tiffin, Catering)
- [x] Featured dishes carousel with your photos
- [x] Unlimited Breakfast offer banner
- [x] Testimonials slider
- [x] Locations grid
- [x] Multiple CTAs

### Table Booking (`/table-booking`)
- [x] Region/Center selection (India/Australia)
- [x] Date picker (min 2hr advance, max 30 days)
- [x] Time slots (12PM-10PM)
- [x] Guest details + celebration type
- [x] Menu pre-ordering for Perth
- [x] WhatsApp confirmation

### Tiffin Booking (`/tiffin`)
- [x] Weekly lunch box subscriptions
- [x] Heavy brunch with drink addons
- [x] **Unlimited Breakfast**: ₹299 (India) / $35 (Perth)
- [x] Perth blackout dates (Dec 15 - Jan 10)
- [x] GST calculation for India (5%)

### Pickup Orders (`/pickup`)
- [x] **Pickup Date field** (today onwards, max 30 days)
- [x] Pickup Time selection
- [x] Menu from database with fallback to JSON
- [x] Category tabs + search
- [x] Cart management
- [x] Minimum order validation (₹200 / $20)

### Catering Booking (`/catering`)
- [x] 4 Packages: Classic (₹450), Premium (₹600), Special (₹750), Royal Feast (₹950)
- [x] Menu selection per package requirements
- [x] Google Maps link generation
- [x] **NEW: Addon Services**
  - 🍽️ **Crockery & Cutlery Rental**: ₹3,000/hr (India) / $200/hr (Perth)
    - Plates, Bowls, Spoons, Serving Dishes
    - Return by 9 AM next morning
    - No cleaning needed
    - Closed Tuesdays
  - 👨‍🍳 **Service Staff**: ₹300/person/hr (India) / $50/person/hr (Perth)

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

## Your Google Drive Images (Used)
- Hero: `1IiJw4VxwbygR2WXSymVgd9S7FoIfrdil`
- Kaju Curry: `1rYkehXEPrE9I4jf1QnaICJscFd3Vso2v`
- Bharit: `1RwL7pG0gZa6VlRY_hdPJAUfXNKCezU2V`
- Maswadi: `168pHmUxU4vyqA4DrplT0_9R_DDK9eK0c`
- Patodi: `1VYDK8vRc_hVR4jn1CsabdBL0fFF4EWaH`

URL format: `https://lh3.googleusercontent.com/d/FILE_ID`

## 📋 Backlog
- [ ] Payment Integration (Razorpay/Stripe)
- [ ] More Google Drive photos integration
- [ ] Push notifications
- [ ] Order history
