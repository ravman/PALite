# GateKeeper - Smart Community Management Platform

## Overview
GateKeeper is a comprehensive, multi-tenant platform for gated community management with three applications:

| App | URL | Purpose |
|-----|-----|---------|
| **Resident App** | `/resident.html` | Residents manage community life |
| **Admin Console** | `/admin.html` | Society administrators manage operations |
| **Guard App** | `/guard.html` | Security personnel at gates |

## Quick Start

```bash
cd backend
python3 seed.py      # Initialize database with sample data
python3 app.py       # Start server on port 3001
```

Then open:
- Resident App: http://localhost:3001/resident.html
- Admin Console: http://localhost:3001/admin.html
- Guard App: http://localhost:3001/guard.html

## Demo Accounts (OTP: 123456 for all)

| Phone | Name | Role | Society |
|-------|------|------|---------|
| 9876543210 | Rahul Mehta | Owner (2 societies) | Green Valley + Sunrise |
| 9876543211 | Priya Patel | Owner | Green Valley |
| 9876543212 | Amit Kumar | Tenant | Green Valley |
| 9876543213 | Sneha Reddy | Family Member | Green Valley |
| 9876543214 | Vikram Singh | Owner + Pending Tenant | Sunrise + Green Valley |
| 9999900001 | Admin Sharma | Admin | Green Valley |
| 9999900003 | Admin Desai | Admin | Sunrise Heights |
| 9999900002 | Raju Guard | Guard | Green Valley |
| 9999900004 | Mohan Guard | Guard | Sunrise Heights |

## Tech Stack
- **Backend**: Python 3 + Flask + SQLite
- **Frontend**: React 18 (CDN) + Babel (in-browser JSX)
- **Auth**: Phone + OTP (simulated, always 123456)
- **Payments**: Stubbed (always succeeds)
- **Smart Locks**: Tuya integration stubbed

## Multi-Tenancy Architecture

### Key Design Principles
1. **Society is the tenant boundary** - every data table includes `society_id`
2. **Roles are per-society** via `user_society_roles` table - a user can be:
   - Admin in Society A
   - Resident in Society B
   - Guard in Society C
3. **Context switching** - users with multiple properties can switch active apartment/society
4. **All queries are scoped** - admin sees only their society's data, guards only their society's entries

### Data Model
```
Society (tenant)
  ├── Towers
  │     └── Apartments
  ├── Spaces (bookable)
  ├── Daily Help
  ├── Document Requirements
  └── Users (via user_society_roles)
        ├── Residents (user-apartment mapping)
        ├── Vehicles
        ├── Pets
        ├── Bookings → Invoices → Payments
        ├── Visitor Invitations
        ├── Marketplace Posts
        ├── Move Requests
        └── Lease Extensions
```

## Features

### Resident App
- **Auth**: Phone + OTP signin/signup with document upload
- **Profile**: View/edit profile, see all properties across societies
- **Context Switch**: Switch between apartments/societies
- **Bookings**: Browse spaces, book time slots, pay (simulated), view invoices
- **Visitors**: Create invitations with QR codes, approve/reject entry requests
- **Marketplace**: Buy/sell posts scoped to current society
- **Vehicles & Pets**: Self-registration
- **Move Requests**: Request move in/out with date ranges
- **Family & Tenants**: Invite family members and tenants
- **Smart Locks**: Unlock gates (Tuya stub)

### Management Console
- **Dashboard**: Stats overview (residents, pending approvals, moves, leases)
- **Residents**: View all, filter by status, approve/reject signups
- **Spaces**: CRUD spaces with pricing, capacity, hours
- **Bookings**: View all bookings across the society
- **Approvals**: Approve/reject move requests and lease extensions
- **Daily Help**: Register, approve, assign to apartments with schedules
- **Documents**: Review and verify/reject uploaded documents
- **Doc Requirements**: Configure mandatory documents per resident type

### Guard App
- **Scan QR**: Verify visitor invitations and daily help QR codes
- **Manual Entry**: Create entry requests for walk-ins (guest, cab, delivery, daily help)
- **Entry Log**: View all entries with status filters, mark exits
- **Delivery Tracking**: Multi-apartment delivery management with per-apartment approvals

## API Endpoints (60+)

### Auth
- `POST /api/auth/request-otp` - Send OTP
- `POST /api/auth/verify-otp` - Verify and get token
- `GET /api/auth/me` - Current user context
- `POST /api/auth/signup` - Register with documents
- `POST /api/context/switch` - Switch apartment/society

### Resident
- `GET/PUT /api/residents/profile` - Profile management
- `POST /api/residents/invite-family` - Invite family member
- `POST /api/residents/invite-tenant` - Invite tenant
- `GET/POST/DELETE /api/residents/vehicles` - Vehicle management
- `GET/POST/DELETE /api/residents/pets` - Pet management

### Bookings
- `GET /api/spaces` - List spaces (society-scoped)
- `GET /api/spaces/:id/availability` - Check availability
- `POST /api/bookings` - Create booking
- `POST /api/bookings/:id/pay` - Pay for booking
- `GET /api/bookings/my` - My bookings
- `POST /api/bookings/:id/cancel` - Cancel booking

### Visitors
- `POST /api/visitors/invite` - Create invitation with QR
- `GET /api/visitors/my-invitations` - My invitations
- `GET /api/visitors/pending-approvals` - Pending approvals
- `POST /api/visitors/:id/approve|reject` - Handle entry

### Marketplace, Documents, Moves, Leases
- Full CRUD for all entities, society-scoped

### Admin (all society-scoped via auth)
- Dashboard, Residents, Spaces, Bookings, Move Requests, Lease Extensions, Daily Help, Documents, Document Requirements

### Guard (all society-scoped)
- QR Scan, Entry Creation, Entry Log, Delivery Tracking

## Database Schema (22 tables)
See `backend/schema.py` for complete schema. Key tables:
- `societies`, `towers`, `apartments` - Property hierarchy
- `users`, `user_society_roles` - Multi-tenant auth
- `residents` - User-apartment mapping with type and status
- `spaces`, `bookings`, `invoices`, `payments` - Booking system
- `visitor_invitations`, `visitor_entries`, `delivery_apartments` - Visitor management
- `daily_help`, `daily_help_apartments` - Daily help management
- `documents`, `document_requirements` - Document management
- `marketplace_posts`, `move_requests`, `lease_extensions` - Other features

## Assumptions
1. OTP is simulated (always "123456") - integrate SMS provider for production
2. Payment gateway is stubbed - integrate Razorpay/Stripe for production
3. Tuya smart lock integration is stubbed - implement via Tuya Cloud SDK
4. Documents stored as text references in DB - use S3/cloud storage in production
5. QR codes are text strings - generate actual QR images via library in production
6. No real-time push notifications - add WebSocket/FCM for production
7. SQLite for MVP - migrate to PostgreSQL for production
8. Sessions don't expire - add TTL for production

## Production Roadmap
1. Replace SQLite with PostgreSQL
2. Add Redis for session management
3. Integrate Razorpay/Stripe payments
4. Integrate Tuya Cloud SDK for smart locks
5. Add SMS OTP via Twilio/MSG91
6. Add push notifications via FCM
7. Generate QR code images
8. File upload to S3/CloudFlare R2
9. Add rate limiting and proper security
10. Build native mobile apps (React Native)
11. Add real-time notifications via WebSocket
12. Add audit logging
