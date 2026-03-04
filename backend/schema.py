import sqlite3, os, uuid
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gatekeeper.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS societies (id TEXT PRIMARY KEY, name TEXT NOT NULL, address TEXT, city TEXT, state TEXT, pincode TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS towers (id TEXT PRIMARY KEY, society_id TEXT NOT NULL, name TEXT NOT NULL, floors INTEGER DEFAULT 10, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS apartments (id TEXT PRIMARY KEY, tower_id TEXT NOT NULL, unit_number TEXT NOT NULL, floor INTEGER, bedrooms INTEGER DEFAULT 2, area_sqft REAL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, phone TEXT UNIQUE NOT NULL, name TEXT, email TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS user_society_roles (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, society_id TEXT NOT NULL, role TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, society_id, role));
CREATE TABLE IF NOT EXISTS residents (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, apartment_id TEXT NOT NULL, society_id TEXT NOT NULL, resident_type TEXT NOT NULL, status TEXT DEFAULT 'pending', invited_by TEXT, lease_start DATE, lease_end DATE, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, apartment_id));
CREATE TABLE IF NOT EXISTS otp_sessions (id TEXT PRIMARY KEY, phone TEXT NOT NULL, otp TEXT NOT NULL, verified INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, resident_id TEXT, society_id TEXT NOT NULL, doc_type TEXT NOT NULL, file_name TEXT, file_data TEXT, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS document_requirements (id TEXT PRIMARY KEY, society_id TEXT NOT NULL, resident_type TEXT NOT NULL, doc_type TEXT NOT NULL, is_mandatory INTEGER DEFAULT 1, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS vehicles (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, apartment_id TEXT, society_id TEXT NOT NULL, vehicle_type TEXT, make TEXT, model TEXT, color TEXT, registration_number TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS pets (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, apartment_id TEXT, society_id TEXT NOT NULL, pet_type TEXT, name TEXT, breed TEXT, age_years REAL, vaccinated INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS spaces (id TEXT PRIMARY KEY, society_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT, space_type TEXT, capacity INTEGER DEFAULT 1, is_shared INTEGER DEFAULT 0, total_spots INTEGER DEFAULT 1, cost_per_hour REAL DEFAULT 0, available_from TEXT DEFAULT '06:00', available_to TEXT DEFAULT '22:00', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS bookings (id TEXT PRIMARY KEY, space_id TEXT NOT NULL, user_id TEXT NOT NULL, society_id TEXT NOT NULL, spot_number INTEGER DEFAULT 1, booking_date DATE NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, status TEXT DEFAULT 'pending', total_cost REAL DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY, booking_id TEXT, user_id TEXT NOT NULL, society_id TEXT NOT NULL, amount REAL NOT NULL, description TEXT, status TEXT DEFAULT 'unpaid', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, invoice_id TEXT NOT NULL, user_id TEXT NOT NULL, society_id TEXT NOT NULL, amount REAL NOT NULL, payment_method TEXT DEFAULT 'gateway', transaction_id TEXT, status TEXT DEFAULT 'success', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS visitor_invitations (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, apartment_id TEXT NOT NULL, society_id TEXT NOT NULL, visitor_name TEXT NOT NULL, visitor_phone TEXT, visitor_type TEXT DEFAULT 'guest', purpose TEXT, qr_code TEXT UNIQUE, valid_from DATETIME, valid_to DATETIME, is_recurring INTEGER DEFAULT 0, status TEXT DEFAULT 'active', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS visitor_entries (id TEXT PRIMARY KEY, invitation_id TEXT, visitor_name TEXT NOT NULL, visitor_phone TEXT, visitor_type TEXT DEFAULT 'guest', apartment_id TEXT, society_id TEXT NOT NULL, guard_user_id TEXT, entry_time DATETIME DEFAULT CURRENT_TIMESTAMP, exit_time DATETIME, approval_status TEXT DEFAULT 'pending', notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS delivery_apartments (id TEXT PRIMARY KEY, entry_id TEXT NOT NULL, apartment_id TEXT NOT NULL, approval_status TEXT DEFAULT 'pending', approved_by TEXT);
CREATE TABLE IF NOT EXISTS marketplace_posts (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, society_id TEXT NOT NULL, post_type TEXT, title TEXT NOT NULL, description TEXT, price REAL, images TEXT, status TEXT DEFAULT 'active', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS move_requests (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, apartment_id TEXT NOT NULL, society_id TEXT NOT NULL, move_type TEXT, tentative_start DATE, tentative_end DATE, status TEXT DEFAULT 'pending', notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS lease_extensions (id TEXT PRIMARY KEY, resident_id TEXT NOT NULL, society_id TEXT NOT NULL, current_end DATE, requested_end DATE, status TEXT DEFAULT 'pending', notes TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS daily_help (id TEXT PRIMARY KEY, society_id TEXT NOT NULL, name TEXT NOT NULL, phone TEXT, help_type TEXT, id_code TEXT, qr_code TEXT, photo TEXT, status TEXT DEFAULT 'pending', created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS daily_help_apartments (id TEXT PRIMARY KEY, daily_help_id TEXT NOT NULL, apartment_id TEXT NOT NULL, days_of_week TEXT DEFAULT 'mon,tue,wed,thu,fri,sat', time_slot TEXT);
CREATE TABLE IF NOT EXISTS user_active_context (user_id TEXT PRIMARY KEY, apartment_id TEXT, society_id TEXT);
"""
def uid(prefix=''):
    return f"{prefix}{uuid.uuid4().hex[:8]}"
def init_db():
    conn = sqlite3.connect(DB_PATH); conn.executescript(SCHEMA); conn.commit(); conn.close()
def get_conn():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; conn.execute('PRAGMA foreign_keys = ON'); return conn
def dr(row):
    return dict(row) if row else None
def drs(rows):
    return [dict(r) for r in rows]
if __name__ == '__main__':
    init_db(); print('DB initialized')
