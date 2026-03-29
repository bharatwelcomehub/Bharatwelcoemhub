# Test Credentials

## Super Admin
- Mobile: 9741399190
- OTP: 123456
- Center: PB-MGT
- Roles: All access (super admin)

## Franchise Owner (Test Account)
- Mobile: 8888888888
- OTP: 123456
- Center: PB-HSR
- Role Key: franchise_owner
- Franchise Code: FR-TEST-INDIA
- Mapped Center: PB-HSR (auto-resolved from DB)
- Revenue Share: 15%

## Auth Flow
1. POST /api/send_otp with {"mobile":"...", "center":"..."}
2. POST /api/verify_otp with {"mobile":"...", "otp":"123456", "center":"..."}
3. Returns token for authenticated requests
