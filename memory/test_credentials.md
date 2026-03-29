# Test Credentials

## Super Admin
- Center: PB-MGT
- Mobile: 9741399190
- OTP: 123456

## Login Flow
1. POST /api/send_otp with {"center": "PB-MGT", "mobile": "9741399190"}
2. POST /api/verify_otp with {"center": "PB-MGT", "mobile": "9741399190", "otp": "123456"}
3. Returns token for authenticated requests
