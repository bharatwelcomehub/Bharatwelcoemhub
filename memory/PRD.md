# Purnabramha IntraPB - Product Requirements Document

## Original Problem Statement
User had existing HTML/Python files for an attendance and salary management system using Excel as database storage. Required migration to MongoDB with modern UI design while preserving all functionality. Added Guest Response AI feature, Bhojan Guru with recipes from user's PDF file, Recipe Admin panel for MGT, and HR Letters generation.

## Project Overview
**Purnabramha IntraPB** - Internal portal for attendance, salary management, HR documents, and guest response for Purnabramha Restaurant Chain (Manswini Foods Pvt. Ltd.)

## What's Been Implemented

### Latest Update (Mar 26, 2026 - Session 25)

- **UPDATE HOURLY RATE UI (COMPLETE)**
  - Pencil icon next to Rate column in International Attendance table
  - Click opens modal with employee name, category, current rate
  - Input for new hourly rate with Save/Cancel buttons
  - Backend endpoint: POST /api/international-attendance/update-rate (JSON body)

- **CENTER CODE MISMATCH FIX (COMPLETE)**
  - Production has center code `PB-PERTH-` (trailing hyphen) but employees stored as `PB-PERTH`
  - Added `normalize_center_code()` and `center_code_variants()` helpers
  - All 7 query points in international_attendance.py now handle both variants
  - No live data modified — only query logic changed

- **DUPLICATE PB-PERTH CENTER FIX (COMPLETE)**
  - Removed duplicate PB-PERTH entry, merged currency/GST fields

- **PAYSLIP PDF TEXT OVERLAP FIX (COMPLETE)**
  - Raised box_bottom from 1.8" to 2.2", repositioned footer to 1.15"
  - Recurring issue (4x) now resolved

### Previous Sessions
(See earlier PRD versions for full history of Sessions 1-24)

## Key Technical Notes
- Center code normalization: `PB-PERTH-` and `PB-PERTH` are treated as equivalent
- Object Storage: Emergent internal library for file attachments
- WhatsApp Integration: MOCKED

## Testing Credentials
- Super Admin: Center PB-MGT, Mobile 9741399190, OTP 123456
- Perth Manager: Center PB-PERTH, Mobile 0401832922, OTP 123456

## Backlog/Future Tasks

### P1 - Upcoming
- PDF export for International payroll reports
- Complete server.py refactoring (extract HR letters & centers/managers routes)
- Test expense attachment file upload flow visually

### P2 - Improvements
- 7-year retention deletion prompt for attachments
- Frontend Babel build fix

### P3 - Future
- Image Upload for Recipes
- Franchise Deal Simulator
- Real WhatsApp Business API integration (currently MOCKED)

## Test Reports
- /app/test_reports/iteration_20.json - Session 25: Update Rate, Duplicate Fix, Payslip Fix (100% pass)
