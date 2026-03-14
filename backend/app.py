import os, sys, uuid
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import init_db, get_conn, dr, drs, uid
from push import (notify_visitor_arrived, notify_visitor_decision,
                  notify_news_published, notify_booking_confirmed,
                  notify_invoice_raised, notify_payment_received)

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
init_db()

def get_db():
    if 'db' not in g: g.db = get_conn()
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db: db.close()

@app.after_request
def cors(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return resp

@app.before_request
def handle_options():
    if request.method == 'OPTIONS': return '', 204

def auth_required(f):
    @wraps(f)
    def dec(*a, **kw):
        token = request.headers.get('Authorization','').replace('Bearer ','')
        if not token: return jsonify({'error':'No token'}), 401
        db = get_db()
        sess = dr(db.execute('SELECT * FROM otp_sessions WHERE id=? AND verified=1',(token,)).fetchone())
        if not sess: return jsonify({'error':'Invalid session'}), 401
        user = dr(db.execute('SELECT * FROM users WHERE phone=?',(sess['phone'],)).fetchone())
        if not user: return jsonify({'error':'User not found'}), 401
        g.user = user
        ctx = dr(db.execute('SELECT * FROM user_active_context WHERE user_id=?',(user['id'],)).fetchone())
        g.apt = ctx['apartment_id'] if ctx else None
        g.soc = ctx['society_id'] if ctx else None
        g.roles = [r['role'] for r in drs(db.execute('SELECT role FROM user_society_roles WHERE user_id=? AND society_id=?',(user['id'], g.soc or '')).fetchall())]
        return f(*a, **kw)
    return dec

def admin_required(f):
    @wraps(f)
    @auth_required
    def dec(*a, **kw):
        if 'admin' not in g.roles and 'super_admin' not in g.roles: return jsonify({'error':'Admin access required'}), 403
        return f(*a, **kw)
    return dec

def guard_required(f):
    @wraps(f)
    @auth_required
    def dec(*a, **kw):
        if 'guard' not in g.roles: return jsonify({'error':'Guard access required'}), 403
        return f(*a, **kw)
    return dec

def no_cache(resp):
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/')
def index(): return no_cache(send_from_directory('../frontend', 'resident.html'))
@app.route('/guard')
def guard_app(): return no_cache(send_from_directory('../frontend', 'guard.html'))
@app.route('/admin')
def admin_app(): return no_cache(send_from_directory('../frontend', 'admin.html'))
@app.route('/<path:fn>')
def static_f(fn): return send_from_directory('../frontend', fn)

@app.route('/api/auth/request-otp', methods=['POST'])
def req_otp():
    phone = request.json.get('phone')
    if not phone: return jsonify({'error':'Phone required'}), 400
    sid = uid('otp-'); db = get_db()
    db.execute('INSERT INTO otp_sessions VALUES(?,?,?,0,CURRENT_TIMESTAMP)',(sid,phone,'123456')); db.commit()
    return jsonify({'success':True,'message':'OTP sent (use 123456)','sessionId':sid})

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    d = request.json; db = get_db()
    sess = dr(db.execute('SELECT * FROM otp_sessions WHERE id=?',(d.get('sessionId'),)).fetchone())
    if not sess: return jsonify({'error':'Invalid session'}), 400
    if sess['otp'] != d.get('otp'): return jsonify({'error':'Invalid OTP'}), 400
    db.execute('UPDATE otp_sessions SET verified=1 WHERE id=?',(sess['id'],))
    user = dr(db.execute('SELECT * FROM users WHERE phone=?',(sess['phone'],)).fetchone())
    is_new = not user
    if not user:
        user_id = uid('usr-'); db.execute('INSERT INTO users(id,phone) VALUES(?,?)',(user_id,sess['phone']))
        user = dr(db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone())
    roles = drs(db.execute('SELECT usr.*, s.name as society_name FROM user_society_roles usr JOIN societies s ON usr.society_id=s.id WHERE usr.user_id=?',(user['id'],)).fetchall())
    # Auto-set active context if none exists (guards/admins have no apartment)
    ctx = dr(db.execute('SELECT * FROM user_active_context WHERE user_id=?',(user['id'],)).fetchone())
    if not ctx and roles:
        db.execute('INSERT OR REPLACE INTO user_active_context VALUES(?,?,?)',(user['id'],None,roles[0]['society_id']))
    db.commit()
    return jsonify({'token':sess['id'],'user':user,'isNew':is_new,'roles':roles})

@app.route('/api/auth/me')
@auth_required
def auth_me():
    db = get_db(); apt=tower=society=resident=None
    if g.apt:
        apt = dr(db.execute('SELECT * FROM apartments WHERE id=?',(g.apt,)).fetchone())
        if apt: tower = dr(db.execute('SELECT * FROM towers WHERE id=?',(apt['tower_id'],)).fetchone())
    if g.soc: society = dr(db.execute('SELECT * FROM societies WHERE id=?',(g.soc,)).fetchone())
    if g.apt: resident = dr(db.execute('SELECT * FROM residents WHERE user_id=? AND apartment_id=?',(g.user['id'],g.apt)).fetchone())
    roles = drs(db.execute('SELECT usr.*, s.name as society_name FROM user_society_roles usr JOIN societies s ON usr.society_id=s.id WHERE usr.user_id=?',(g.user['id'],)).fetchall())
    return jsonify({'user':g.user,'apartment':apt,'tower':tower,'society':society,'resident':resident,'roles':roles,'activeSociety':g.soc,'activeApartment':g.apt})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    d = request.json; db = get_db()
    sess = dr(db.execute('SELECT * FROM otp_sessions WHERE id=? AND verified=1',(d.get('token'),)).fetchone())
    if not sess: return jsonify({'error':'Invalid session'}), 401
    user = dr(db.execute('SELECT * FROM users WHERE phone=?',(sess['phone'],)).fetchone())
    if not user: return jsonify({'error':'User not found'}), 400
    db.execute('UPDATE users SET name=?, email=? WHERE id=?',(d.get('name'),d.get('email'),user['id']))
    apt = dr(db.execute('SELECT a.*, t.society_id FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE a.id=?',(d.get('apartmentId'),)).fetchone())
    if not apt: return jsonify({'error':'Apartment not found'}), 400
    soc_id = apt['society_id']; res_id = uid('res-')
    db.execute('INSERT INTO residents(id,user_id,apartment_id,society_id,resident_type,status) VALUES(?,?,?,?,?,?)',(res_id,user['id'],d['apartmentId'],soc_id,d.get('residentType','owner'),'pending'))
    try: db.execute('INSERT INTO user_society_roles VALUES(?,?,?,?,CURRENT_TIMESTAMP)',(uid('ur-'),user['id'],soc_id,'resident'))
    except: pass
    db.execute('INSERT OR REPLACE INTO user_active_context VALUES(?,?,?)',(user['id'],d['apartmentId'],soc_id))
    for doc in d.get('documents',[]):
        db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(uid('doc-'),user['id'],res_id,soc_id,doc.get('type'),doc.get('fileName'),doc.get('data'),'pending'))
    db.commit()
    return jsonify({'success':True,'residentId':res_id,'status':'pending'})

@app.route('/api/context/switch', methods=['POST'])
@auth_required
def switch_context():
    d = request.json; db = get_db(); apt_id = d.get('apartmentId'); soc_id = d.get('societyId')
    if apt_id:
        apt = dr(db.execute('SELECT a.*, t.society_id FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE a.id=?',(apt_id,)).fetchone())
        if apt: soc_id = apt['society_id']
    db.execute('INSERT OR REPLACE INTO user_active_context VALUES(?,?,?)',(g.user['id'],apt_id,soc_id)); db.commit()
    return jsonify({'success':True})

@app.route('/api/residents/profile')
@auth_required
def get_profile():
    db = get_db()
    res = drs(db.execute("SELECT r.*, a.unit_number, t.name as tower_name, s.name as society_name, s.id as society_id FROM residents r JOIN apartments a ON r.apartment_id=a.id JOIN towers t ON a.tower_id=t.id JOIN societies s ON t.society_id=s.id WHERE r.user_id=?",(g.user['id'],)).fetchall())
    vehs = drs(db.execute('SELECT * FROM vehicles WHERE user_id=? AND society_id=?',(g.user['id'],g.soc or '')).fetchall())
    pets = drs(db.execute('SELECT * FROM pets WHERE user_id=? AND society_id=?',(g.user['id'],g.soc or '')).fetchall())
    invs = drs(db.execute('SELECT i.*, b.booking_date, b.start_time, b.end_time FROM invoices i LEFT JOIN bookings b ON i.booking_id=b.id WHERE i.user_id=? AND i.society_id=? ORDER BY i.created_at DESC',(g.user['id'],g.soc or '')).fetchall())
    pays = drs(db.execute('SELECT p.*, i.description FROM payments p JOIN invoices i ON p.invoice_id=i.id WHERE p.user_id=? AND p.society_id=? ORDER BY p.created_at DESC',(g.user['id'],g.soc or '')).fetchall())
    fam=[]; ten=[]
    if g.apt:
        fam = drs(db.execute("SELECT r.*, u.name, u.phone FROM residents r JOIN users u ON r.user_id=u.id WHERE r.apartment_id=? AND r.resident_type='family_member'",(g.apt,)).fetchall())
        ten = drs(db.execute("SELECT r.*, u.name, u.phone FROM residents r JOIN users u ON r.user_id=u.id WHERE r.apartment_id=? AND r.resident_type='tenant'",(g.apt,)).fetchall())
    return jsonify({'user':g.user,'residencies':res,'vehicles':vehs,'pets':pets,'invoices':invs,'payments':pays,'family':fam,'tenants':ten})

@app.route('/api/residents/profile', methods=['PUT'])
@auth_required
def update_profile():
    d = request.json; db = get_db()
    db.execute('UPDATE users SET name=?, email=? WHERE id=?',(d.get('name'),d.get('email'),g.user['id'])); db.commit()
    return jsonify({'success':True})

@app.route('/api/residents/invite-family', methods=['POST'])
@auth_required
def invite_family():
    d = request.json; db = get_db()
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    user = dr(db.execute('SELECT * FROM users WHERE phone=?',(d['phone'],)).fetchone())
    if not user:
        u_id = uid('usr-'); db.execute('INSERT INTO users(id,phone,name) VALUES(?,?,?)',(u_id,d['phone'],d['name'])); user = {'id':u_id}
    res_id = uid('res-')
    try:
        db.execute('INSERT INTO residents(id,user_id,apartment_id,society_id,resident_type,status,invited_by) VALUES(?,?,?,?,?,?,?)',(res_id,user['id'],g.apt,g.soc,'family_member','pending',g.user['id']))
        try: db.execute('INSERT INTO user_society_roles VALUES(?,?,?,?,CURRENT_TIMESTAMP)',(uid('ur-'),user['id'],g.soc,'resident'))
        except: pass
        db.commit()
    except: return jsonify({'error':'Already a resident'}), 400
    return jsonify({'success':True,'residentId':res_id})

@app.route('/api/residents/invite-tenant', methods=['POST'])
@auth_required
def invite_tenant():
    d = request.json; db = get_db()
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    user = dr(db.execute('SELECT * FROM users WHERE phone=?',(d['phone'],)).fetchone())
    if not user:
        u_id = uid('usr-'); db.execute('INSERT INTO users(id,phone,name) VALUES(?,?,?)',(u_id,d['phone'],d['name'])); user = {'id':u_id}
    res_id = uid('res-')
    try:
        db.execute('INSERT INTO residents(id,user_id,apartment_id,society_id,resident_type,status,invited_by,lease_start,lease_end) VALUES(?,?,?,?,?,?,?,?,?)',(res_id,user['id'],g.apt,g.soc,'tenant','pending',g.user['id'],d.get('leaseStart'),d.get('leaseEnd')))
        try: db.execute('INSERT INTO user_society_roles VALUES(?,?,?,?,CURRENT_TIMESTAMP)',(uid('ur-'),user['id'],g.soc,'resident'))
        except: pass
        db.commit()
    except: return jsonify({'error':'Already a resident'}), 400
    return jsonify({'success':True,'residentId':res_id})

@app.route('/api/residents/vehicles')
@auth_required
def get_vehicles(): return jsonify(drs(get_db().execute('SELECT * FROM vehicles WHERE user_id=? AND society_id=?',(g.user['id'],g.soc or '')).fetchall()))

@app.route('/api/residents/vehicles', methods=['POST'])
@auth_required
def add_vehicle():
    d = request.json; db = get_db(); vid = uid('veh-')
    db.execute('INSERT INTO vehicles VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(vid,g.user['id'],g.apt,g.soc,d.get('vehicleType'),d.get('make'),d.get('model'),d.get('color'),d.get('registrationNumber'))); db.commit()
    return jsonify({'success':True,'id':vid})

@app.route('/api/residents/vehicles/<vid>', methods=['DELETE'])
@auth_required
def del_vehicle(vid): get_db().execute('DELETE FROM vehicles WHERE id=? AND user_id=?',(vid,g.user['id'])); get_db().commit(); return jsonify({'success':True})

@app.route('/api/residents/pets')
@auth_required
def get_pets(): return jsonify(drs(get_db().execute('SELECT * FROM pets WHERE user_id=? AND society_id=?',(g.user['id'],g.soc or '')).fetchall()))

@app.route('/api/residents/pets', methods=['POST'])
@auth_required
def add_pet():
    d = request.json; db = get_db(); pid = uid('pet-')
    db.execute('INSERT INTO pets VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(pid,g.user['id'],g.apt,g.soc,d.get('petType'),d.get('name'),d.get('breed'),d.get('ageYears'),1 if d.get('vaccinated') else 0)); db.commit()
    return jsonify({'success':True,'id':pid})

@app.route('/api/residents/pets/<pid>', methods=['DELETE'])
@auth_required
def del_pet(pid): get_db().execute('DELETE FROM pets WHERE id=? AND user_id=?',(pid,g.user['id'])); get_db().commit(); return jsonify({'success':True})

@app.route('/api/spaces')
@auth_required
def get_spaces():
    if not g.soc: return jsonify([])
    return jsonify(drs(get_db().execute('SELECT * FROM spaces WHERE society_id=?',(g.soc,)).fetchall()))

@app.route('/api/spaces/<sid>/availability')
@auth_required
def space_avail(sid):
    date = request.args.get('date')
    if not date: return jsonify({'error':'Date required'}), 400
    db = get_db()
    space = dr(db.execute('SELECT * FROM spaces WHERE id=? AND society_id=?',(sid,g.soc)).fetchone())
    booked = drs(db.execute("SELECT * FROM bookings WHERE space_id=? AND booking_date=? AND status IN ('pending','confirmed')",(sid,date)).fetchall())
    return jsonify({'space':space,'bookedSlots':booked,'date':date})

@app.route('/api/bookings', methods=['POST'])
@auth_required
def create_booking():
    d = request.json; db = get_db()
    space = dr(db.execute('SELECT * FROM spaces WHERE id=? AND society_id=?',(d['spaceId'],g.soc)).fetchone())
    if not space: return jsonify({'error':'Space not found'}), 404
    spot = d.get('spotNumber',1)
    conflict = db.execute("SELECT id FROM bookings WHERE space_id=? AND booking_date=? AND spot_number=? AND status IN ('pending','confirmed') AND NOT (end_time <= ? OR start_time >= ?)",(d['spaceId'],d['date'],spot,d['startTime'],d['endTime'])).fetchone()
    if conflict: return jsonify({'error':'Slot already booked'}), 400
    hours = max(1, int(d['endTime'].split(':')[0]) - int(d['startTime'].split(':')[0]))
    cost = hours * space['cost_per_hour']
    bk_id = uid('bk-'); inv_id = uid('inv-')
    db.execute('INSERT INTO bookings VALUES(?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(bk_id,d['spaceId'],g.user['id'],g.soc,spot,d['date'],d['startTime'],d['endTime'],'pending',cost))
    db.execute('INSERT INTO invoices VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(inv_id,bk_id,g.user['id'],g.soc,cost,f"{space['name']} - {d['date']} {d['startTime']}-{d['endTime']}",'unpaid'))
    db.commit()
    return jsonify({'bookingId':bk_id,'invoiceId':inv_id,'totalCost':cost})

@app.route('/api/bookings/<bk_id>/pay', methods=['POST'])
@auth_required
def pay_booking(bk_id):
    db = get_db()
    bk = dr(db.execute('SELECT * FROM bookings WHERE id=? AND user_id=?',(bk_id,g.user['id'])).fetchone())
    if not bk: return jsonify({'error':'Booking not found'}), 404
    inv = dr(db.execute('SELECT * FROM invoices WHERE booking_id=?',(bk_id,)).fetchone())
    space = dr(db.execute('SELECT name FROM spaces WHERE id=?',(bk['space_id'],)).fetchone())
    pay_id = uid('pay-'); txn = 'TXN_' + uuid.uuid4().hex[:12].upper()
    db.execute('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(pay_id,inv['id'],g.user['id'],g.soc,inv['amount'],'gateway',txn,'success'))
    db.execute("UPDATE invoices SET status='paid' WHERE id=?",(inv['id'],))
    db.execute("UPDATE bookings SET status='confirmed' WHERE id=?",(bk_id,))
    db.commit()
    notify_booking_confirmed(db, g.user['id'],
        space['name'] if space else 'Space',
        bk['booking_date'], bk_id)
    return jsonify({'success':True,'paymentId':pay_id,'transactionId':txn})

@app.route('/api/bookings/my')
@auth_required
def my_bookings():
    return jsonify(drs(get_db().execute("SELECT b.*, s.name as space_name, s.space_type, i.id as invoice_id, i.status as invoice_status FROM bookings b JOIN spaces s ON b.space_id=s.id LEFT JOIN invoices i ON i.booking_id=b.id WHERE b.user_id=? AND b.society_id=? ORDER BY b.booking_date DESC",(g.user['id'],g.soc or '')).fetchall()))

@app.route('/api/bookings/<bk_id>/cancel', methods=['POST'])
@auth_required
def cancel_booking(bk_id):
    db = get_db()
    db.execute("UPDATE bookings SET status='cancelled' WHERE id=? AND user_id=?",(bk_id,g.user['id']))
    inv = dr(db.execute('SELECT * FROM invoices WHERE booking_id=?',(bk_id,)).fetchone())
    if inv: db.execute("UPDATE invoices SET status='cancelled' WHERE id=?",(inv['id'],))
    db.commit()
    return jsonify({'success':True})

@app.route('/api/auth/push-token', methods=['POST'])
@auth_required
def register_push_token():
    token = request.json.get('token','').strip()
    platform = request.json.get('platform','')
    if not token or not token.startswith('ExponentPushToken'):
        return jsonify({'error':'Invalid Expo push token'}), 400
    db = get_db(); tid = uid('pt-')
    # Upsert: delete old record for same token, insert fresh
    db.execute("DELETE FROM push_tokens WHERE token=?", (token,))
    db.execute("INSERT INTO push_tokens VALUES(?,?,?,?,CURRENT_TIMESTAMP)",
               (tid, g.user['id'], token, platform))
    db.commit()
    return jsonify({'success': True})


@app.route('/api/visitors/create-invite', methods=['POST'])
@auth_required
def invite_visitor():
    d = request.json; db = get_db()
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    vid = uid('vinv-'); qr = 'QR-' + uuid.uuid4().hex[:8].upper()
    visitor_name = d.get('visitorName','').strip()
    if not visitor_name: return jsonify({'error': 'Visitor name is required'}), 400
    db.execute('INSERT INTO visitor_invitations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(vid,g.user['id'],g.apt,g.soc,visitor_name,d.get('visitorPhone'),d.get('visitorType','guest'),d.get('purpose'),qr,d.get('validFrom'),d.get('validTo'),1 if d.get('isRecurring') else 0,'active'))
    db.commit()
    return jsonify({'id':vid,'qrCode':qr})

@app.route('/api/visitors/my-invitations')
@auth_required
def my_invitations():
    return jsonify(drs(get_db().execute('SELECT * FROM visitor_invitations WHERE user_id=? AND society_id=? ORDER BY created_at DESC',(g.user['id'],g.soc or '')).fetchall()))

@app.route('/api/visitors/my-entries')
@auth_required
def my_entries():
    db = get_db()
    if not g.apt: return jsonify([])
    date = request.args.get('date', '')
    tab  = request.args.get('tab', 'expected')  # expected | inside | history
    if tab == 'inside':
        # Currently checked in (entry_time set, exit_time null, approved)
        rows = drs(db.execute(
            "SELECT ve.*, u.name as resident_name FROM visitor_entries ve "
            "LEFT JOIN users u ON u.id=(SELECT user_id FROM residents WHERE apartment_id=ve.apartment_id LIMIT 1) "
            "WHERE ve.apartment_id=? AND ve.exit_time IS NULL AND ve.approval_status='approved' "
            "ORDER BY ve.entry_time DESC", (g.apt,)).fetchall())
    elif tab == 'history':
        rows = drs(db.execute(
            "SELECT ve.* FROM visitor_entries ve "
            "WHERE ve.apartment_id=? AND (ve.exit_time IS NOT NULL OR ve.approval_status IN ('rejected')) "
            "ORDER BY ve.created_at DESC LIMIT 50", (g.apt,)).fetchall())
    else:
        # Expected: all entries for apartment on a date, or invitations valid for date
        if date:
            rows = drs(db.execute(
                "SELECT ve.* FROM visitor_entries ve "
                "WHERE ve.apartment_id=? AND date(ve.created_at)=? "
                "ORDER BY ve.created_at DESC", (g.apt, date)).fetchall())
        else:
            rows = drs(db.execute(
                "SELECT ve.* FROM visitor_entries ve "
                "WHERE ve.apartment_id=? AND date(ve.created_at)=date('now','localtime') "
                "ORDER BY ve.created_at DESC", (g.apt,)).fetchall())
    return jsonify(rows)

@app.route('/api/visitors/pending-approvals')
@auth_required
def pending_approvals():
    db = get_db()
    if not g.apt: return jsonify({'entries':[],'deliveries':[]})
    entries = drs(db.execute("SELECT * FROM visitor_entries WHERE apartment_id=? AND approval_status='pending' ORDER BY created_at DESC",(g.apt,)).fetchall())
    deliveries = drs(db.execute("SELECT da.*, ve.visitor_name, ve.visitor_type, ve.entry_time FROM delivery_apartments da JOIN visitor_entries ve ON da.entry_id=ve.id WHERE da.apartment_id=? AND da.approval_status='pending'",(g.apt,)).fetchall())
    return jsonify({'entries':entries,'deliveries':deliveries})

@app.route('/api/visitors/<vid>/approve', methods=['POST'])
@auth_required
def approve_visitor(vid):
    db = get_db()
    entry = dr(db.execute("SELECT * FROM visitor_entries WHERE id=?", (vid,)).fetchone())
    db.execute("UPDATE visitor_entries SET approval_status='approved' WHERE id=?", (vid,))
    db.commit()
    if entry:
        notify_visitor_decision(db, g.user['id'], entry['visitor_name'], True, vid)
    return jsonify({'success': True})

@app.route('/api/visitors/<vid>/reject', methods=['POST'])
@auth_required
def reject_visitor(vid):
    db = get_db()
    entry = dr(db.execute("SELECT * FROM visitor_entries WHERE id=?", (vid,)).fetchone())
    db.execute("UPDATE visitor_entries SET approval_status='rejected' WHERE id=?", (vid,))
    db.commit()
    if entry:
        notify_visitor_decision(db, g.user['id'], entry['visitor_name'], False, vid)
    return jsonify({'success': True})

@app.route('/api/visitors/delivery/<did>/approve', methods=['POST'])
@auth_required
def approve_delivery(did): get_db().execute("UPDATE delivery_apartments SET approval_status='approved', approved_by=? WHERE id=?",(g.user['id'],did)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/visitors/invitations/<vid>', methods=['DELETE'])
@auth_required
def cancel_invitation(vid): get_db().execute("UPDATE visitor_invitations SET status='cancelled' WHERE id=? AND user_id=?",(vid,g.user['id'])); get_db().commit(); return jsonify({'success':True})

@app.route('/api/marketplace')
@auth_required
def marketplace():
    import json as _json
    if not g.soc: return jsonify([])
    posts = drs(get_db().execute("SELECT mp.*, u.name as posted_by FROM marketplace_posts mp JOIN users u ON mp.user_id=u.id WHERE mp.society_id=? AND mp.status='active' ORDER BY mp.created_at DESC",(g.soc,)).fetchall())
    for p in posts:
        try: p['images'] = _json.loads(p['images']) if p.get('images') else []
        except: p['images'] = []
    return jsonify(posts)

@app.route('/api/marketplace', methods=['POST'])
@auth_required
def create_post():
    d = request.json; db = get_db(); pid = uid('mp-')
    if not g.soc: return jsonify({'error':'No active society'}), 400
    images = d.get('images') # list of base64 strings or URLs
    images_json = __import__('json').dumps(images) if images else None
    db.execute('INSERT INTO marketplace_posts VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(pid,g.user['id'],g.soc,d.get('postType'),d['title'],d.get('description'),d.get('price'),images_json,'active')); db.commit()
    return jsonify({'success':True,'id':pid})

@app.route('/api/marketplace/<pid>', methods=['DELETE'])
@auth_required
def close_post(pid): get_db().execute("UPDATE marketplace_posts SET status='closed' WHERE id=? AND user_id=?",(pid,g.user['id'])); get_db().commit(); return jsonify({'success':True})

@app.route('/api/documents/upload', methods=['POST'])
@auth_required
def upload_doc():
    d = request.json; db = get_db(); did = uid('doc-')
    db.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(did,g.user['id'],d.get('residentId'),g.soc,d.get('docType'),d.get('fileName'),d.get('fileData'),'pending')); db.commit()
    return jsonify({'success':True,'id':did})

@app.route('/api/documents/my')
@auth_required
def my_docs(): return jsonify(drs(get_db().execute('SELECT id,user_id,resident_id,doc_type,file_name,status,created_at FROM documents WHERE user_id=? AND society_id=?',(g.user['id'],g.soc or '')).fetchall()))

@app.route('/api/documents/requirements')
@auth_required
def doc_reqs(): return jsonify(drs(get_db().execute('SELECT * FROM document_requirements WHERE society_id=?',(g.soc or '',)).fetchall()))

@app.route('/api/public/doc-requirements')
def public_doc_reqs():
    """No auth needed — used during signup to show required docs before login."""
    soc_id = request.args.get('societyId')
    res_type = request.args.get('residentType')
    if not soc_id or not res_type: return jsonify([])
    return jsonify(drs(get_db().execute(
        'SELECT * FROM document_requirements WHERE society_id=? AND resident_type=?',
        (soc_id, res_type)).fetchall()))

@app.route('/api/move-requests', methods=['POST'])
@auth_required
def create_move():
    d = request.json; db = get_db(); mid = uid('mv-')
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    db.execute('INSERT INTO move_requests VALUES(?,?,?,?,?,?,?,?,?,NULL,CURRENT_TIMESTAMP)',
               (mid,g.user['id'],g.apt,g.soc,d.get('moveType'),d.get('tentativeStart'),d.get('tentativeEnd'),'pending',d.get('notes')))
    # Save documents submitted with the request
    for doc in d.get('documents',[]):
        db.execute('INSERT INTO move_documents VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',
                   (uid('mvd-'), mid, g.user['id'], g.soc, doc.get('type'), doc.get('fileName'), doc.get('data'), 'pending'))
    db.commit()
    return jsonify({'success':True,'id':mid})

@app.route('/api/move-requests/my')
@auth_required
def my_moves():
    db = get_db()
    moves = drs(db.execute('SELECT * FROM move_requests WHERE user_id=? AND society_id=? ORDER BY created_at DESC',(g.user['id'],g.soc or '')).fetchall())
    for m in moves:
        m['documents'] = drs(db.execute('SELECT id,doc_type,file_name,status FROM move_documents WHERE move_request_id=?',(m['id'],)).fetchall())
    return jsonify(moves)

@app.route('/api/public/move-doc-requirements')
def public_move_doc_reqs():
    """No auth — used in the move request form to show required docs."""
    soc_id   = request.args.get('societyId')
    move_type = request.args.get('moveType')
    if not soc_id or not move_type: return jsonify([])
    return jsonify(drs(get_db().execute(
        'SELECT * FROM move_doc_requirements WHERE society_id=? AND move_type=?',
        (soc_id, move_type)).fetchall()))

@app.route('/api/lease/extend', methods=['POST'])
@auth_required
def extend_lease():
    d = request.json; db = get_db()
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    res = dr(db.execute("SELECT * FROM residents WHERE user_id=? AND apartment_id=? AND resident_type='tenant'",(g.user['id'],g.apt)).fetchone())
    if not res: return jsonify({'error':'Not a tenant'}), 400
    lid = uid('le-')
    db.execute('INSERT INTO lease_extensions VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(lid,res['id'],g.soc,res['lease_end'],d.get('requestedEnd'),'pending',d.get('notes'))); db.commit()
    return jsonify({'success':True,'id':lid})

@app.route('/api/lease/my-extensions')
@auth_required
def my_extensions(): return jsonify(drs(get_db().execute("SELECT le.*, r.apartment_id FROM lease_extensions le JOIN residents r ON le.resident_id=r.id WHERE r.user_id=? AND le.society_id=?",(g.user['id'],g.soc or '')).fetchall()))

@app.route('/api/smart-lock/unlock', methods=['POST'])
@auth_required
def unlock(): return jsonify({'success':True,'message':'Lock unlocked (simulated)'})

@app.route('/api/smart-lock/status')
@auth_required
def lock_status(): return jsonify({'locks':[{'id':'lock-main-gate','name':'Main Gate','status':'locked','battery':85},{'id':'lock-parking','name':'Parking Gate','status':'locked','battery':72}]})

# ==================== ADMIN ENDPOINTS ====================
@app.route('/api/admin/dashboard')
@admin_required
def admin_dashboard():
    db = get_db(); s = g.soc
    if not s: return jsonify({})
    total = db.execute('SELECT COUNT(*) as c FROM residents WHERE society_id=?',(s,)).fetchone()['c']
    pending = db.execute("SELECT COUNT(*) as c FROM residents WHERE society_id=? AND status='pending'",(s,)).fetchone()['c']
    pmoves = db.execute("SELECT COUNT(*) as c FROM move_requests WHERE society_id=? AND status='pending'",(s,)).fetchone()['c']
    pleases = db.execute("SELECT COUNT(*) as c FROM lease_extensions WHERE society_id=? AND status='pending'",(s,)).fetchone()['c']
    dhelp = db.execute("SELECT COUNT(*) as c FROM daily_help WHERE society_id=? AND status='approved'",(s,)).fetchone()['c']
    pdocs = db.execute("SELECT COUNT(*) as c FROM documents WHERE society_id=? AND status='pending'",(s,)).fetchone()['c']
    return jsonify({'totalResidents':total,'pendingApprovals':pending,'pendingMoves':pmoves,'pendingLeases':pleases,'activeDailyHelp':dhelp,'pendingDocuments':pdocs})

@app.route('/api/admin/societies')
@admin_required
def admin_societies():
    return jsonify(drs(get_db().execute("SELECT s.* FROM societies s JOIN user_society_roles usr ON s.id=usr.society_id WHERE usr.user_id=? AND usr.role IN ('admin','super_admin')",(g.user['id'],)).fetchall()))

@app.route('/api/admin/towers')
@admin_required
def admin_towers(): return jsonify(drs(get_db().execute('SELECT * FROM towers WHERE society_id=?',(g.soc,)).fetchall()))

@app.route('/api/admin/apartments')
@admin_required
def admin_apartments():
    tid = request.args.get('towerId'); db = get_db()
    if tid: return jsonify(drs(db.execute('SELECT a.*, t.name as tower_name FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE a.tower_id=? AND t.society_id=?',(tid,g.soc)).fetchall()))
    return jsonify(drs(db.execute('SELECT a.*, t.name as tower_name FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE t.society_id=? ORDER BY t.name, a.floor, a.unit_number',(g.soc,)).fetchall()))

@app.route('/api/admin/apartments', methods=['POST'])
@admin_required
def admin_create_apartment():
    d = request.json; db = get_db()
    if not d.get('towerId') or not d.get('unitNumber'): return jsonify({'error': 'towerId and unitNumber required'}), 400
    # Verify tower belongs to this society
    tower = dr(db.execute('SELECT * FROM towers WHERE id=? AND society_id=?', (d['towerId'], g.soc)).fetchone())
    if not tower: return jsonify({'error': 'Tower not found'}), 404
    aid = uid('apt-')
    db.execute('INSERT INTO apartments(id,tower_id,unit_number,floor,bedrooms,area_sqft) VALUES(?,?,?,?,?,?)',
               (aid, d['towerId'], d['unitNumber'], d.get('floor'), d.get('bedrooms', 2), d.get('areaSqft')))
    db.commit()
    return jsonify({'success': True, 'id': aid})

@app.route('/api/admin/apartments/<aid>', methods=['PUT'])
@admin_required
def admin_update_apartment(aid):
    d = request.json; db = get_db()
    apt = dr(db.execute('SELECT a.* FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE a.id=? AND t.society_id=?', (aid, g.soc)).fetchone())
    if not apt: return jsonify({'error': 'Not found'}), 404
    db.execute('UPDATE apartments SET unit_number=?, floor=?, bedrooms=?, area_sqft=? WHERE id=?',
               (d.get('unitNumber', apt['unit_number']), d.get('floor', apt['floor']),
                d.get('bedrooms', apt['bedrooms']), d.get('areaSqft', apt['area_sqft']), aid))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/apartments/<aid>', methods=['DELETE'])
@admin_required
def admin_delete_apartment(aid):
    db = get_db()
    apt = dr(db.execute('SELECT a.* FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE a.id=? AND t.society_id=?', (aid, g.soc)).fetchone())
    if not apt: return jsonify({'error': 'Not found'}), 404
    if dr(db.execute('SELECT id FROM residents WHERE apartment_id=? AND status="approved"', (aid,)).fetchone()):
        return jsonify({'error': 'Cannot delete apartment with active residents'}), 400
    db.execute('DELETE FROM apartments WHERE id=?', (aid,))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/apartments/<aid>/residents')
@admin_required
def admin_apartment_residents(aid):
    db = get_db()
    # Verify apartment belongs to this society
    apt = dr(db.execute('SELECT a.* FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE a.id=? AND t.society_id=?', (aid, g.soc)).fetchone())
    if not apt: return jsonify({'error': 'Not found'}), 404
    rows = drs(db.execute(
        'SELECT r.*, u.name, u.phone, u.email FROM residents r JOIN users u ON r.user_id=u.id WHERE r.apartment_id=? ORDER BY r.status, r.created_at DESC',
        (aid,)).fetchall())
    return jsonify(rows)



@app.route('/api/admin/residents')
@admin_required
def admin_residents():
    status = request.args.get('status'); db = get_db()
    sql = "SELECT r.*, u.name, u.phone, u.email, a.unit_number, t.name as tower_name FROM residents r JOIN users u ON r.user_id=u.id JOIN apartments a ON r.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE r.society_id=?"
    p = [g.soc]
    if status: sql += ' AND r.status=?'; p.append(status)
    sql += ' ORDER BY r.created_at DESC'
    return jsonify(drs(db.execute(sql, p).fetchall()))

@app.route('/api/admin/residents/<rid>/approve', methods=['POST'])
@admin_required
def admin_approve_res(rid):
    db = get_db()
    res = dr(db.execute("SELECT * FROM residents WHERE id=? AND society_id=?", (rid, g.soc)).fetchone())
    if not res: return jsonify({'error': 'Not found'}), 404
    db.execute("UPDATE residents SET status='approved', rejection_reason=NULL WHERE id=?", (rid,))
    db.commit()
    from push import _get_tokens_for_user, send_push
    tokens = _get_tokens_for_user(db, res['user_id'])
    send_push(tokens, '✅ Residency Approved!', 'Your application has been approved. Welcome to the community!',
              {'type': 'residency_approved', 'screen': 'Home'})
    return jsonify({'success': True})

@app.route('/api/admin/residents/<rid>/reject', methods=['POST'])
@admin_required
def admin_reject_res(rid):
    d = request.json or {}
    reason = (d.get('reason') or '').strip()
    if not reason: return jsonify({'error': 'Rejection reason is required'}), 400
    db = get_db()
    res = dr(db.execute("SELECT * FROM residents WHERE id=? AND society_id=?", (rid, g.soc)).fetchone())
    if not res: return jsonify({'error': 'Not found'}), 404
    db.execute("UPDATE residents SET status='rejected', rejection_reason=? WHERE id=?", (reason, rid))
    db.commit()
    from push import _get_tokens_for_user, send_push
    tokens = _get_tokens_for_user(db, res['user_id'])
    send_push(tokens, '❌ Application Not Approved', f'Reason: {reason}',
              {'type': 'residency_rejected', 'reason': reason, 'screen': 'Home'})
    return jsonify({'success': True})

@app.route('/api/residents/status')
@auth_required
def resident_status():
    """For pending/rejected residents to poll their approval status."""
    db = get_db()
    res = dr(db.execute(
        "SELECT r.*, a.unit_number, t.name as tower_name, s.name as society_name "
        "FROM residents r JOIN apartments a ON r.apartment_id=a.id "
        "JOIN towers t ON a.tower_id=t.id JOIN societies s ON r.society_id=s.id "
        "WHERE r.user_id=? ORDER BY r.created_at DESC LIMIT 1", (g.user['id'],)).fetchone())
    return jsonify(res or {})

@app.route('/api/admin/spaces')
@admin_required
def admin_spaces(): return jsonify(drs(get_db().execute('SELECT * FROM spaces WHERE society_id=?',(g.soc,)).fetchall()))

@app.route('/api/admin/spaces', methods=['POST'])
@admin_required
def admin_add_space():
    d = request.json; db = get_db(); sid = uid('spc-')
    db.execute('INSERT INTO spaces VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(sid,g.soc,d['name'],d.get('description'),d.get('spaceType'),d.get('capacity',1),1 if d.get('isShared') else 0,d.get('totalSpots',1),d.get('costPerHour',0),d.get('availableFrom','06:00'),d.get('availableTo','22:00'))); db.commit()
    return jsonify({'success':True,'id':sid})

@app.route('/api/admin/spaces/<sid>', methods=['PUT'])
@admin_required
def admin_edit_space(sid):
    d = request.json; db = get_db()
    db.execute('UPDATE spaces SET name=?,description=?,cost_per_hour=?,capacity=?,available_from=?,available_to=?,total_spots=? WHERE id=? AND society_id=?',(d['name'],d.get('description'),d.get('costPerHour'),d.get('capacity'),d.get('availableFrom'),d.get('availableTo'),d.get('totalSpots'),sid,g.soc)); db.commit()
    return jsonify({'success':True})

@app.route('/api/admin/spaces/<sid>', methods=['DELETE'])
@admin_required
def admin_del_space(sid): get_db().execute('DELETE FROM spaces WHERE id=? AND society_id=?',(sid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/bookings')
@admin_required
def admin_bookings():
    return jsonify(drs(get_db().execute("SELECT b.*, s.name as space_name, u.name as booked_by FROM bookings b JOIN spaces s ON b.space_id=s.id JOIN users u ON b.user_id=u.id WHERE b.society_id=? ORDER BY b.booking_date DESC",(g.soc,)).fetchall()))

@app.route('/api/admin/move-requests')
@admin_required
def admin_moves():
    db = get_db()
    moves = drs(db.execute(
        "SELECT mr.*, u.name, u.phone, a.unit_number, t.name as tower_name "
        "FROM move_requests mr JOIN users u ON mr.user_id=u.id "
        "JOIN apartments a ON mr.apartment_id=a.id JOIN towers t ON a.tower_id=t.id "
        "WHERE mr.society_id=? ORDER BY mr.created_at DESC", (g.soc,)).fetchall())
    for m in moves:
        m['documents'] = drs(db.execute(
            'SELECT id, doc_type, file_name, status, data FROM move_documents WHERE move_request_id=?',
            (m['id'],)).fetchall())
    return jsonify(moves)

@app.route('/api/admin/move-requests/<mid>/approve', methods=['POST'])
@admin_required
def admin_approve_move(mid):
    db = get_db()
    mv = dr(db.execute("SELECT * FROM move_requests WHERE id=? AND society_id=?", (mid, g.soc)).fetchone())
    if not mv: return jsonify({'error':'Not found'}), 404
    db.execute("UPDATE move_requests SET status='approved', rejection_reason=NULL WHERE id=?", (mid,))
    db.commit()
    from push import _get_tokens_for_user, send_push
    label = 'Move In' if mv.get('move_type') == 'move_in' else 'Move Out'
    send_push(_get_tokens_for_user(db, mv['user_id']),
              f'✅ {label} Approved',
              f'Your {label.lower()} request has been approved.',
              {'type': 'move_approved', 'screen': 'Visitors'})
    return jsonify({'success': True})

@app.route('/api/admin/move-requests/<mid>/reject', methods=['POST'])
@admin_required
def admin_reject_move(mid):
    d = request.json or {}
    reason = (d.get('reason') or '').strip()
    if not reason: return jsonify({'error': 'Rejection reason is required'}), 400
    db = get_db()
    mv = dr(db.execute("SELECT * FROM move_requests WHERE id=? AND society_id=?", (mid, g.soc)).fetchone())
    if not mv: return jsonify({'error':'Not found'}), 404
    db.execute("UPDATE move_requests SET status='rejected', rejection_reason=? WHERE id=?", (reason, mid))
    db.commit()
    from push import _get_tokens_for_user, send_push
    label = 'Move In' if mv.get('move_type') == 'move_in' else 'Move Out'
    send_push(_get_tokens_for_user(db, mv['user_id']),
              f'❌ {label} Not Approved', f'Reason: {reason}',
              {'type': 'move_rejected', 'reason': reason, 'screen': 'Visitors'})
    return jsonify({'success': True})

@app.route('/api/admin/move-requests/<mid>/documents/<did>/verify', methods=['POST'])
@admin_required
def admin_verify_move_doc(mid, did):
    get_db().execute("UPDATE move_documents SET status='verified' WHERE id=? AND society_id=?", (did, g.soc))
    get_db().commit()
    return jsonify({'success': True})

# ─── Move Doc Requirements ────────────────────────────────────────────────────
@app.route('/api/admin/move-doc-requirements')
@admin_required
def admin_move_doc_reqs():
    return jsonify(drs(get_db().execute(
        'SELECT * FROM move_doc_requirements WHERE society_id=? ORDER BY move_type, doc_type', (g.soc,)).fetchall()))

@app.route('/api/admin/move-doc-requirements', methods=['POST'])
@admin_required
def admin_add_move_doc_req():
    d = request.json; db = get_db()
    if not d.get('moveType') or not d.get('docType'): return jsonify({'error':'moveType and docType required'}), 400
    did = uid('mdr-')
    db.execute('INSERT INTO move_doc_requirements VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)',
               (did, g.soc, d['moveType'], d['docType'], 1 if d.get('isMandatory', True) else 0))
    db.commit()
    return jsonify({'success': True, 'id': did})

@app.route('/api/admin/move-doc-requirements/<did>', methods=['DELETE'])
@admin_required
def admin_del_move_doc_req(did):
    get_db().execute('DELETE FROM move_doc_requirements WHERE id=? AND society_id=?', (did, g.soc))
    get_db().commit()
    return jsonify({'success': True})

# --- Lease doc requirements ---------------------------------------------------
@app.route('/api/admin/lease-doc-requirements')
@admin_required
def admin_lease_doc_reqs():
    return jsonify(drs(get_db().execute(
        'SELECT * FROM lease_doc_requirements WHERE society_id=? ORDER BY doc_type', (g.soc,)).fetchall()))

@app.route('/api/admin/lease-doc-requirements', methods=['POST'])
@admin_required
def admin_add_lease_doc_req():
    d = request.json or {}
    db = get_db()
    did = uid('ldr-')
    db.execute('INSERT INTO lease_doc_requirements VALUES(?,?,?,?,CURRENT_TIMESTAMP)',
               (did, g.soc, d['docType'], 1 if d.get('isMandatory', True) else 0))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/lease-doc-requirements/<did>', methods=['DELETE'])
@admin_required
def admin_del_lease_doc_req(did):
    get_db().execute('DELETE FROM lease_doc_requirements WHERE id=? AND society_id=?', (did, g.soc))
    get_db().commit()
    return jsonify({'success': True})

@app.route('/api/public/lease-doc-requirements')
def public_lease_doc_reqs():
    sid = request.args.get('societyId', '')
    return jsonify(drs(get_db().execute(
        'SELECT * FROM lease_doc_requirements WHERE society_id=?', (sid,)).fetchall()))

# --- Lease documents (resident upload) ----------------------------------------
@app.route('/api/lease-extensions/<lid>/documents', methods=['POST'])
@auth_required
def upload_lease_doc(lid):
    d = request.json or {}
    db = get_db()
    le = dr(db.execute('SELECT * FROM lease_extensions WHERE id=? AND society_id=?', (lid, g.soc or '')).fetchone())
    if not le: return jsonify({'error': 'Not found'}), 404
    did = uid('ldoc-')
    db.execute('INSERT INTO lease_documents VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',
               (did, lid, g.soc, d.get('docType'), d.get('fileName'), d.get('data'), 'pending'))
    db.commit()
    return jsonify({'success': True, 'id': did})

@app.route('/api/admin/lease-extensions/<lid>/documents')
@admin_required
def admin_lease_docs(lid):
    return jsonify(drs(get_db().execute(
        'SELECT * FROM lease_documents WHERE lease_extension_id=? AND society_id=?',
        (lid, g.soc)).fetchall()))

@app.route('/api/admin/lease-extensions/<lid>/documents/<did>/verify', methods=['POST'])
@admin_required
def admin_verify_lease_doc(lid, did):
    db = get_db()
    db.execute("UPDATE lease_documents SET status='verified' WHERE id=? AND society_id=?", (did, g.soc))
    db.commit()
    return jsonify({'success': True})


@admin_required
def admin_leases():
    return jsonify(drs(get_db().execute("SELECT le.*, u.name, u.phone, a.unit_number, t.name as tower_name FROM lease_extensions le JOIN residents r ON le.resident_id=r.id JOIN users u ON r.user_id=u.id JOIN apartments a ON r.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE le.society_id=? ORDER BY le.created_at DESC",(g.soc,)).fetchall()))

@app.route('/api/admin/lease-extensions/<lid>/approve', methods=['POST'])
@admin_required
def admin_approve_lease(lid):
    db = get_db()
    le = dr(db.execute('SELECT * FROM lease_extensions WHERE id=? AND society_id=?',(lid,g.soc)).fetchone())
    if le:
        db.execute("UPDATE lease_extensions SET status='approved' WHERE id=?",(lid,))
        db.execute("UPDATE residents SET lease_end=? WHERE id=?",(le['requested_end'],le['resident_id']))
        db.commit()
    return jsonify({'success':True})

@app.route('/api/admin/lease-extensions/<lid>/reject', methods=['POST'])
@admin_required
def admin_reject_lease(lid): get_db().execute("UPDATE lease_extensions SET status='rejected' WHERE id=? AND society_id=?",(lid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/daily-help')
@admin_required
def admin_daily_help():
    db = get_db()
    helpers = drs(db.execute('SELECT * FROM daily_help WHERE society_id=? ORDER BY created_at DESC',(g.soc,)).fetchall())
    for h in helpers:
        h['assignments'] = drs(db.execute("SELECT dha.*, a.unit_number, t.name as tower_name FROM daily_help_apartments dha JOIN apartments a ON dha.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE dha.daily_help_id=?",(h['id'],)).fetchall())
    return jsonify(helpers)

@app.route('/api/admin/daily-help', methods=['POST'])
@admin_required
def admin_add_help():
    d = request.json; db = get_db(); hid = uid('dh-')
    ic = 'DH-' + uuid.uuid4().hex[:6].upper(); qr = 'QR-DH-' + uuid.uuid4().hex[:6].upper()
    db.execute('INSERT INTO daily_help VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(hid,g.soc,d['name'],d.get('phone'),d.get('helpType'),ic,qr,None,'pending')); db.commit()
    return jsonify({'success':True,'id':hid,'idCode':ic,'qrCode':qr})

@app.route('/api/admin/daily-help/<hid>/approve', methods=['POST'])
@admin_required
def admin_approve_help(hid): get_db().execute("UPDATE daily_help SET status='approved' WHERE id=? AND society_id=?",(hid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/daily-help/<hid>/reject', methods=['POST'])
@admin_required
def admin_reject_help(hid): get_db().execute("UPDATE daily_help SET status='rejected' WHERE id=? AND society_id=?",(hid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/daily-help/<hid>/assign', methods=['POST'])
@admin_required
def admin_assign_help(hid):
    d = request.json; db = get_db(); aid = uid('dha-')
    db.execute('INSERT INTO daily_help_apartments VALUES(?,?,?,?,?)',(aid,hid,d['apartmentId'],d.get('daysOfWeek','mon,tue,wed,thu,fri,sat'),d.get('timeSlot'))); db.commit()
    return jsonify({'success':True,'id':aid})

@app.route('/api/admin/document-requirements')
@admin_required
def admin_doc_reqs(): return jsonify(drs(get_db().execute('SELECT * FROM document_requirements WHERE society_id=?',(g.soc,)).fetchall()))

@app.route('/api/admin/document-requirements', methods=['POST'])
@admin_required
def admin_add_doc_req():
    d = request.json; db = get_db(); did = uid('dreq-')
    db.execute('INSERT INTO document_requirements VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)',(did,g.soc,d['residentType'],d['docType'],1 if d.get('isMandatory',True) else 0)); db.commit()
    return jsonify({'success':True,'id':did})

@app.route('/api/admin/document-requirements/<did>', methods=['DELETE'])
@admin_required
def admin_del_doc_req(did): get_db().execute('DELETE FROM document_requirements WHERE id=? AND society_id=?',(did,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/residents/<rid>/documents')
@admin_required
def admin_resident_docs(rid):
    db = get_db()
    docs = drs(db.execute(
        'SELECT id, doc_type, file_name, status, data, created_at FROM documents WHERE resident_id=? AND society_id=? ORDER BY created_at DESC',
        (rid, g.soc)
    ).fetchall())
    return jsonify(docs)

@app.route('/api/admin/documents')
@admin_required
def admin_docs():
    return jsonify(drs(get_db().execute("SELECT d.id, d.doc_type, d.file_name, d.status, d.created_at, u.name, u.phone, r.resident_type, a.unit_number FROM documents d JOIN users u ON d.user_id=u.id LEFT JOIN residents r ON d.resident_id=r.id LEFT JOIN apartments a ON r.apartment_id=a.id WHERE d.society_id=? ORDER BY d.created_at DESC",(g.soc,)).fetchall()))

@app.route('/api/admin/documents/<did>/verify', methods=['POST'])
@admin_required
def admin_verify_doc(did): get_db().execute("UPDATE documents SET status='verified' WHERE id=? AND society_id=?",(did,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/documents/<did>/reject', methods=['POST'])
@admin_required
def admin_reject_doc(did): get_db().execute("UPDATE documents SET status='rejected' WHERE id=? AND society_id=?",(did,g.soc)); get_db().commit(); return jsonify({'success':True})

# ==================== GUARD ENDPOINTS ====================
# ─── Resident: Invoices & Payments ───────────────────────────────────────────
@app.route('/api/payments/invoices')
@auth_required
def my_invoices():
    """All invoices for the current user in the current society."""
    db = get_db()
    # Direct invoices (booking-based or individually raised)
    rows = drs(db.execute(
        "SELECT i.*, p.id as payment_id, p.transaction_id, p.created_at as paid_at, p.amount as paid_amount "
        "FROM invoices i "
        "LEFT JOIN payments p ON p.invoice_id=i.id AND p.user_id=i.user_id "
        "WHERE i.user_id=? AND i.society_id=? ORDER BY i.created_at DESC",
        (g.user['id'], g.soc or '')).fetchall())
    # Bulk invoices via invoice_residents
    bulk = drs(db.execute(
        "SELECT i.*, ir.status as ir_status, ir.paid_at, "
        "p.id as payment_id, p.transaction_id, p.amount as paid_amount "
        "FROM invoice_residents ir "
        "JOIN invoices i ON ir.invoice_id=i.id "
        "LEFT JOIN payments p ON p.invoice_id=i.id AND p.user_id=? "
        "WHERE ir.user_id=? AND i.society_id=? ORDER BY i.created_at DESC",
        (g.user['id'], g.user['id'], g.soc or '')).fetchall())
    # Merge, deduplicate by id, bulk invoices use ir_status as effective status
    seen = set()
    merged = []
    for inv in rows:
        if inv['id'] not in seen:
            seen.add(inv['id']); merged.append(inv)
    for inv in bulk:
        if inv['id'] not in seen:
            inv['status'] = inv.get('ir_status') or inv['status']
            seen.add(inv['id']); merged.append(inv)
    merged.sort(key=lambda x: x['created_at'], reverse=True)
    return jsonify(merged)

@app.route('/api/payments/pay/<inv_id>', methods=['POST'])
@auth_required
def pay_invoice(inv_id):
    """Pay a standalone or bulk invoice."""
    db = get_db()
    # Try direct invoice first
    inv = dr(db.execute("SELECT * FROM invoices WHERE id=? AND society_id=?",
                        (inv_id, g.soc)).fetchone())
    if not inv: return jsonify({'error': 'Invoice not found'}), 404

    # Determine if this is a bulk invoice (has invoice_residents row)
    ir = dr(db.execute("SELECT * FROM invoice_residents WHERE invoice_id=? AND user_id=?",
                       (inv_id, g.user['id'])).fetchone())

    # Check already paid
    already_paid = ir['status'] == 'paid' if ir else inv['status'] == 'paid'
    if already_paid: return jsonify({'error': 'Already paid'}), 400

    pay_id = uid('pay-'); txn = uid('TXN-').upper()
    db.execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
               (pay_id, inv_id, g.user['id'], g.soc, inv['amount'], 'gateway', txn, 'success'))

    if ir:
        db.execute("UPDATE invoice_residents SET status='paid', paid_at=CURRENT_TIMESTAMP WHERE invoice_id=? AND user_id=?",
                   (inv_id, g.user['id']))
        # Mark invoice paid only if everyone has paid
        unpaid = db.execute("SELECT COUNT(*) FROM invoice_residents WHERE invoice_id=? AND status='unpaid'",
                            (inv_id,)).fetchone()[0]
        if unpaid == 0:
            db.execute("UPDATE invoices SET status='paid' WHERE id=?", (inv_id,))
    else:
        db.execute("UPDATE invoices SET status='paid' WHERE id=?", (inv_id,))

    db.commit()
    notify_payment_received(db, g.user['id'], inv.get('title') or inv.get('description','Invoice'),
                            inv['amount'], pay_id)
    return jsonify({'success': True, 'paymentId': pay_id, 'transactionId': txn})

@app.route('/api/payments/receipt/<payment_id>')
@auth_required
def payment_receipt(payment_id):
    db = get_db()
    pay = dr(db.execute(
        "SELECT p.*, i.title, i.description, i.invoice_type, i.amount as invoice_amount, "
        "i.due_date, u.name as resident_name, u.phone, a.unit_number, t.name as tower_name, s.name as society_name "
        "FROM payments p "
        "JOIN invoices i ON p.invoice_id=i.id "
        "JOIN users u ON p.user_id=u.id "
        "JOIN residents r ON r.user_id=p.user_id AND r.society_id=p.society_id "
        "JOIN apartments a ON r.apartment_id=a.id "
        "JOIN towers t ON a.tower_id=t.id "
        "JOIN societies s ON p.society_id=s.id "
        "WHERE p.id=? AND p.user_id=?", (payment_id, g.user['id'])).fetchone())
    if not pay: return jsonify({'error': 'Not found'}), 404
    return jsonify(pay)

# ─── Admin: Invoices & Payments ───────────────────────────────────────────────
@app.route('/api/admin/invoices')
@admin_required
def admin_list_invoices():
    db = get_db()
    status = request.args.get('status')
    sql = ("SELECT i.*, u.name as resident_name, u.phone, "
           "a.unit_number, t.name as tower_name, "
           "(SELECT COUNT(*) FROM invoice_residents WHERE invoice_id=i.id) as recipient_count, "
           "(SELECT COUNT(*) FROM invoice_residents WHERE invoice_id=i.id AND status='paid') as paid_count "
           "FROM invoices i "
           "LEFT JOIN users u ON i.user_id=u.id "
           "LEFT JOIN residents r ON r.user_id=i.user_id AND r.society_id=i.society_id "
           "LEFT JOIN apartments a ON r.apartment_id=a.id "
           "LEFT JOIN towers t ON a.tower_id=t.id "
           "WHERE i.society_id=? AND i.invoice_type != 'booking'")
    p = [g.soc]
    if status: sql += ' AND i.status=?'; p.append(status)
    sql += ' ORDER BY i.created_at DESC'
    invoices = drs(db.execute(sql, p).fetchall())
    return jsonify(invoices)

@app.route('/api/admin/invoices/preview-recipients', methods=['POST'])
@admin_required
def preview_recipients():
    """Preview who will receive the invoice before raising it."""
    d = request.json; db = get_db()
    target = d.get('target', 'all')   # 'all' | 'type' | 'apartment' | 'specific'
    res_types = d.get('residentTypes', [])
    apt_ids = d.get('apartmentIds', [])
    user_ids = d.get('userIds', [])

    sql = ("SELECT r.id as resident_id, r.resident_type, r.user_id, r.apartment_id, "
           "u.name, u.phone, a.unit_number, t.name as tower_name "
           "FROM residents r JOIN users u ON r.user_id=u.id "
           "JOIN apartments a ON r.apartment_id=a.id "
           "JOIN towers t ON a.tower_id=t.id "
           "WHERE r.society_id=? AND r.status='approved'")
    p = [g.soc]

    if target == 'type' and res_types:
        sql += f" AND r.resident_type IN ({','.join('?'*len(res_types))})"
        p.extend(res_types)
    elif target == 'apartment' and apt_ids:
        sql += f" AND r.apartment_id IN ({','.join('?'*len(apt_ids))})"
        p.extend(apt_ids)
    elif target == 'specific' and user_ids:
        sql += f" AND r.user_id IN ({','.join('?'*len(user_ids))})"
        p.extend(user_ids)

    return jsonify(drs(db.execute(sql, p).fetchall()))

@app.route('/api/admin/invoices', methods=['POST'])
@admin_required
def admin_raise_invoice():
    d = request.json; db = get_db()
    if not d.get('title'):  return jsonify({'error': 'title required'}), 400
    if not d.get('amount'): return jsonify({'error': 'amount required'}), 400

    target = d.get('target', 'all')
    res_types = d.get('residentTypes', [])
    apt_ids = d.get('apartmentIds', [])
    user_ids_explicit = d.get('userIds', [])

    # Get recipients
    sql = ("SELECT r.user_id, r.apartment_id FROM residents r "
           "WHERE r.society_id=? AND r.status='approved'")
    p = [g.soc]
    if target == 'type' and res_types:
        sql += f" AND r.resident_type IN ({','.join('?'*len(res_types))})"; p.extend(res_types)
    elif target == 'apartment' and apt_ids:
        sql += f" AND r.apartment_id IN ({','.join('?'*len(apt_ids))})"; p.extend(apt_ids)
    elif target == 'specific' and user_ids_explicit:
        sql += f" AND r.user_id IN ({','.join('?'*len(user_ids_explicit))})"; p.extend(user_ids_explicit)

    recipients = drs(db.execute(sql, p).fetchall())
    # Deduplicate by user_id (a user may have multiple residencies in the society)
    seen_users = {}
    for r in recipients:
        if r['user_id'] not in seen_users:
            seen_users[r['user_id']] = r['apartment_id']

    if not seen_users: return jsonify({'error': 'No eligible residents found'}), 400

    inv_id = uid('inv-')
    amount = float(d['amount'])
    # For single-recipient invoices keep user_id on invoice for backward compat
    single_user = list(seen_users.keys())[0] if len(seen_users) == 1 else None

    db.execute("INSERT INTO invoices VALUES(?,NULL,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
               (inv_id, single_user, g.soc, amount,
                d['title'], d.get('description'), d.get('invoiceType','maintenance'),
                d.get('dueDate'), d.get('notes'), g.user['id'], 'unpaid'))

    for uid_r, apt_id in seen_users.items():
        db.execute("INSERT INTO invoice_residents VALUES(?,?,?,?,?,NULL,CURRENT_TIMESTAMP)",
                   (uid('ir-'), inv_id, uid_r, apt_id, 'unpaid'))

    db.commit()

    # Push notifications
    for uid_r in seen_users:
        notify_invoice_raised(db, uid_r, d['title'], amount, d.get('dueDate'), inv_id)

    return jsonify({'success': True, 'invoiceId': inv_id, 'recipientCount': len(seen_users)})

@app.route('/api/admin/invoices/<inv_id>', methods=['DELETE'])
@admin_required
def admin_cancel_invoice(inv_id):
    db = get_db()
    inv = dr(db.execute("SELECT * FROM invoices WHERE id=? AND society_id=?", (inv_id, g.soc)).fetchone())
    if not inv: return jsonify({'error': 'Not found'}), 404
    if inv['status'] == 'paid': return jsonify({'error': 'Cannot cancel a paid invoice'}), 400
    db.execute("UPDATE invoices SET status='cancelled' WHERE id=?", (inv_id,))
    db.execute("UPDATE invoice_residents SET status='cancelled' WHERE invoice_id=?", (inv_id,))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/invoices/<inv_id>/recipients')
@admin_required
def admin_invoice_recipients(inv_id):
    db = get_db()
    rows = drs(db.execute(
        "SELECT ir.*, u.name, u.phone, a.unit_number, t.name as tower_name, r.resident_type "
        "FROM invoice_residents ir "
        "JOIN users u ON ir.user_id=u.id "
        "JOIN apartments a ON ir.apartment_id=a.id "
        "JOIN towers t ON a.tower_id=t.id "
        "JOIN residents r ON r.user_id=ir.user_id AND r.apartment_id=ir.apartment_id "
        "WHERE ir.invoice_id=? ORDER BY a.unit_number", (inv_id,)).fetchall())
    return jsonify(rows)

@app.route('/api/admin/payments')
@admin_required
def admin_payments():
    db = get_db()
    rows = drs(db.execute(
        "SELECT p.*, i.title, i.invoice_type, u.name as resident_name, u.phone, "
        "a.unit_number, t.name as tower_name "
        "FROM payments p JOIN invoices i ON p.invoice_id=i.id "
        "JOIN users u ON p.user_id=u.id "
        "JOIN residents r ON r.user_id=p.user_id AND r.society_id=p.society_id "
        "JOIN apartments a ON r.apartment_id=a.id "
        "JOIN towers t ON a.tower_id=t.id "
        "WHERE p.society_id=? ORDER BY p.created_at DESC", (g.soc,)).fetchall())
    return jsonify(rows)

# ─── Banners & Ads (resident-facing) ─────────────────────────────────────────
@app.route('/api/home/banners')
@auth_required
def home_banners():
    if not g.soc: return jsonify([])
    rows = drs(get_db().execute(
        "SELECT * FROM society_banners WHERE society_id=? AND is_active=1 "
        "AND (expires_at IS NULL OR expires_at > datetime('now')) "
        "ORDER BY sort_order ASC, created_at DESC", (g.soc,)).fetchall())
    return jsonify(rows)

@app.route('/api/home/ads')
@auth_required
def home_ads():
    if not g.soc: return jsonify([])
    rows = drs(get_db().execute(
        "SELECT * FROM advertisements WHERE society_id=? AND is_active=1 "
        "AND (expires_at IS NULL OR expires_at > datetime('now')) "
        "ORDER BY sort_order ASC, created_at DESC", (g.soc,)).fetchall())
    return jsonify(rows)

# ─── Admin: Banners ────────────────────────────────────────────────────────────
@app.route('/api/admin/banners')
@admin_required
def admin_list_banners():
    return jsonify(drs(get_db().execute(
        "SELECT * FROM society_banners WHERE society_id=? ORDER BY sort_order ASC, created_at DESC", (g.soc,)).fetchall()))

@app.route('/api/admin/banners', methods=['POST'])
@admin_required
def admin_add_banner():
    d = request.json; db = get_db()
    bid = uid('ban-')
    db.execute("INSERT INTO society_banners VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
               (bid, g.soc, d.get('title'), d.get('body'), d.get('imageUrl'),
                d.get('bgColor','#6c5ce7'), d.get('ctaText'), d.get('ctaUrl'),
                1 if d.get('isActive', True) else 0,
                int(d.get('sortOrder', 0)), d.get('expiresAt')))
    db.commit()
    return jsonify({'success': True, 'id': bid})

@app.route('/api/admin/banners/<bid>', methods=['PUT'])
@admin_required
def admin_update_banner(bid):
    d = request.json; db = get_db()
    db.execute("UPDATE society_banners SET title=?,body=?,image_url=?,bg_color=?,cta_text=?,cta_url=?,is_active=?,sort_order=?,expires_at=? WHERE id=? AND society_id=?",
               (d.get('title'), d.get('body'), d.get('imageUrl'), d.get('bgColor','#6c5ce7'),
                d.get('ctaText'), d.get('ctaUrl'), 1 if d.get('isActive', True) else 0,
                int(d.get('sortOrder', 0)), d.get('expiresAt'), bid, g.soc))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/banners/<bid>', methods=['DELETE'])
@admin_required
def admin_del_banner(bid):
    get_db().execute("DELETE FROM society_banners WHERE id=? AND society_id=?", (bid, g.soc))
    get_db().commit()
    return jsonify({'success': True})

# ─── Admin: Advertisements ────────────────────────────────────────────────────
@app.route('/api/admin/ads')
@admin_required
def admin_list_ads():
    return jsonify(drs(get_db().execute(
        "SELECT * FROM advertisements WHERE society_id=? ORDER BY sort_order ASC, created_at DESC", (g.soc,)).fetchall()))

@app.route('/api/admin/ads', methods=['POST'])
@admin_required
def admin_add_ad():
    d = request.json; db = get_db()
    if not d.get('headline'): return jsonify({'error': 'headline required'}), 400
    aid = uid('ad-')
    db.execute("INSERT INTO advertisements VALUES(?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
               (aid, g.soc, d['headline'], d.get('subtext'), d.get('imageUrl'),
                d.get('bgColor','#1a1a2e'), d.get('ctaText'), d.get('ctaUrl'),
                d.get('advertiser'), 1 if d.get('isActive', True) else 0,
                int(d.get('sortOrder', 0)), d.get('expiresAt')))
    db.commit()
    return jsonify({'success': True, 'id': aid})

@app.route('/api/admin/ads/<aid>', methods=['PUT'])
@admin_required
def admin_update_ad(aid):
    d = request.json; db = get_db()
    db.execute("UPDATE advertisements SET headline=?,subtext=?,image_url=?,bg_color=?,cta_text=?,cta_url=?,advertiser=?,is_active=?,sort_order=?,expires_at=? WHERE id=? AND society_id=?",
               (d.get('headline'), d.get('subtext'), d.get('imageUrl'), d.get('bgColor','#1a1a2e'),
                d.get('ctaText'), d.get('ctaUrl'), d.get('advertiser'),
                1 if d.get('isActive', True) else 0, int(d.get('sortOrder', 0)),
                d.get('expiresAt'), aid, g.soc))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/ads/<aid>', methods=['DELETE'])
@admin_required
def admin_del_ad(aid):
    get_db().execute("DELETE FROM advertisements WHERE id=? AND society_id=?", (aid, g.soc))
    get_db().commit()
    return jsonify({'success': True})

# ─── Society News ──────────────────────────────────────────────────────────────
import json as _json

@app.route('/api/news')
@auth_required
def list_news():
    if not g.soc: return jsonify([])
    rows = drs(get_db().execute(
        "SELECT sn.*, u.name as author_name FROM society_news sn JOIN users u ON sn.author_id=u.id WHERE sn.society_id=? ORDER BY sn.is_pinned DESC, sn.created_at DESC",
        (g.soc,)).fetchall())
    for r in rows:
        try: r['images'] = _json.loads(r['images']) if r.get('images') else []
        except: r['images'] = []
    return jsonify(rows)

@app.route('/api/news', methods=['POST'])
@auth_required
def create_news():
    d = request.json; db = get_db()
    if not g.soc: return jsonify({'error': 'No active society'}), 400
    role = dr(db.execute("SELECT role FROM user_society_roles WHERE user_id=? AND society_id=? AND role IN ('admin','super_admin')", (g.user['id'], g.soc)).fetchone())
    if not role: return jsonify({'error': 'Admin access required'}), 403
    nid = uid('news-')
    images = d.get('images', [])
    db.execute("INSERT INTO society_news VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
               (nid, g.soc, g.user['id'], d['title'], d.get('body',''), _json.dumps(images), 1 if d.get('isPinned') else 0, d.get('category','society')))
    db.commit()
    notify_news_published(db, g.soc, d['title'], nid)
    return jsonify({'success': True, 'id': nid})

@app.route('/api/news/<nid>', methods=['DELETE'])
@auth_required
def delete_news(nid):
    db = get_db()
    role = dr(db.execute("SELECT role FROM user_society_roles WHERE user_id=? AND society_id=? AND role IN ('admin','super_admin')", (g.user['id'], g.soc)).fetchone())
    if not role: return jsonify({'error': 'Admin access required'}), 403
    db.execute("DELETE FROM society_news WHERE id=? AND society_id=?", (nid, g.soc))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/news/<nid>/pin', methods=['POST'])
@auth_required
def pin_news(nid):
    db = get_db()
    role = dr(db.execute("SELECT role FROM user_society_roles WHERE user_id=? AND society_id=? AND role IN ('admin','super_admin')", (g.user['id'], g.soc)).fetchone())
    if not role: return jsonify({'error': 'Admin access required'}), 403
    d = request.json or {}
    db.execute("UPDATE society_news SET is_pinned=? WHERE id=? AND society_id=?", (1 if d.get('pin') else 0, nid, g.soc))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/guard/scan-qr', methods=['POST'])
@guard_required
def scan_qr():
    qr = request.json.get('qrCode'); db = get_db()
    inv = dr(db.execute("SELECT vi.*, a.unit_number, t.name as tower_name FROM visitor_invitations vi JOIN apartments a ON vi.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE vi.qr_code=? AND vi.status='active' AND vi.society_id=?",(qr,g.soc)).fetchone())
    if inv: return jsonify({'type':'visitor','invitation':inv})
    dh = dr(db.execute("SELECT * FROM daily_help WHERE qr_code=? AND status='approved' AND society_id=?",(qr,g.soc)).fetchone())
    if dh:
        assigns = drs(db.execute("SELECT dha.*, a.unit_number, t.name as tower_name FROM daily_help_apartments dha JOIN apartments a ON dha.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE dha.daily_help_id=?",(dh['id'],)).fetchall())
        return jsonify({'type':'daily_help','dailyHelp':dh,'assignments':assigns})
    return jsonify({'error':'Invalid QR code'}), 404

@app.route('/api/guard/create-entry', methods=['POST'])
@guard_required
def create_entry():
    d = request.json; db = get_db(); eid = uid('ve-')
    visitor_name = d['visitorName']
    visitor_type = d.get('visitorType','guest')
    apartment_id = d.get('apartmentId')
    db.execute("INSERT INTO visitor_entries VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,NULL,?,?,CURRENT_TIMESTAMP)",
               (eid,d.get('invitationId'),visitor_name,d.get('visitorPhone'),visitor_type,apartment_id,g.soc,g.user['id'],'pending',d.get('notes')))
    if d.get('invitationId'): db.execute("UPDATE visitor_invitations SET status='used' WHERE id=?",(d['invitationId'],))
    delivery_apts = d.get('deliveryApartments',[])
    for apt_id in delivery_apts:
        db.execute('INSERT INTO delivery_apartments VALUES(?,?,?,?,?)',(uid('da-'),eid,apt_id,'pending',None))
    db.commit()
    # Notify residents — single apt or all delivery apts
    apts_to_notify = delivery_apts if delivery_apts else ([apartment_id] if apartment_id else [])
    for apt_id in apts_to_notify:
        notify_visitor_arrived(db, apt_id, visitor_name, visitor_type, eid)
    return jsonify({'success':True,'entryId':eid})

@app.route('/api/guard/entries')
@guard_required
def guard_entries():
    status = request.args.get('status'); db = get_db()
    sql = "SELECT ve.*, a.unit_number, t.name as tower_name FROM visitor_entries ve LEFT JOIN apartments a ON ve.apartment_id=a.id LEFT JOIN towers t ON a.tower_id=t.id WHERE ve.society_id=?"
    p = [g.soc]
    if status: sql += ' AND ve.approval_status=?'; p.append(status)
    sql += ' ORDER BY ve.created_at DESC LIMIT 50'
    return jsonify(drs(db.execute(sql, p).fetchall()))

@app.route('/api/guard/delivery-entries')
@guard_required
def guard_deliveries():
    db = get_db()
    entries = drs(db.execute("SELECT ve.* FROM visitor_entries ve WHERE ve.visitor_type='delivery' AND ve.society_id=? ORDER BY ve.created_at DESC",(g.soc,)).fetchall())
    for e in entries:
        e['apartments'] = drs(db.execute("SELECT da.*, a.unit_number, t.name as tower_name FROM delivery_apartments da JOIN apartments a ON da.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE da.entry_id=?",(e['id'],)).fetchall())
    return jsonify(entries)

@app.route('/api/guard/entries/<eid>/exit', methods=['POST'])
@guard_required
def guard_exit(eid): get_db().execute('UPDATE visitor_entries SET exit_time=CURRENT_TIMESTAMP WHERE id=? AND society_id=?',(eid,g.soc)); get_db().commit(); return jsonify({'success':True})

# ==================== LOOKUP (public) ====================
@app.route('/api/lookup/societies')
def lookup_societies(): return jsonify(drs(get_conn().execute('SELECT id, name, city FROM societies').fetchall()))

@app.route('/api/lookup/towers')
def lookup_towers():
    sid = request.args.get('societyId')
    return jsonify(drs(get_conn().execute('SELECT id, name FROM towers WHERE society_id=?',(sid,)).fetchall()))

@app.route('/api/lookup/apartments')
def lookup_apartments():
    tid = request.args.get('towerId')
    return jsonify(drs(get_conn().execute('SELECT id, unit_number, floor FROM apartments WHERE tower_id=?',(tid,)).fetchall()))

# ==================== SUPER ADMIN - Society Management ====================

def super_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '')
        if not token: return jsonify({'error': 'Unauthorized'}), 401
        db = get_db()
        sess = dr(db.execute('SELECT * FROM otp_sessions WHERE id=? AND verified=1', (token,)).fetchone())
        if not sess: return jsonify({'error': 'Unauthorized'}), 401
        user = dr(db.execute('SELECT * FROM users WHERE phone=?', (sess['phone'],)).fetchone())
        if not user: return jsonify({'error': 'Unauthorized'}), 401
        roles = [r['role'] for r in drs(db.execute('SELECT role FROM user_society_roles WHERE user_id=?', (user['id'],)).fetchall())]
        if 'super_admin' not in roles: return jsonify({'error': 'Super admin access required'}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated

# List all societies
@app.route('/api/superadmin/societies')
@super_admin_required
def sa_list_societies():
    db = get_db()
    societies = drs(db.execute('SELECT * FROM societies ORDER BY created_at DESC').fetchall())
    for s in societies:
        s['towers'] = drs(db.execute('SELECT t.*, COUNT(a.id) as apartment_count FROM towers t LEFT JOIN apartments a ON a.tower_id=t.id WHERE t.society_id=? GROUP BY t.id', (s['id'],)).fetchall())
        s['admin_count'] = db.execute("SELECT COUNT(*) FROM user_society_roles WHERE society_id=? AND role IN ('admin','super_admin')", (s['id'],)).fetchone()[0]
        s['guard_count'] = db.execute("SELECT COUNT(*) FROM user_society_roles WHERE society_id=? AND role='guard'", (s['id'],)).fetchone()[0]
        s['resident_count'] = db.execute("SELECT COUNT(*) FROM residents WHERE society_id=? AND status='approved'", (s['id'],)).fetchone()[0]
    return jsonify(societies)

# Create society
@app.route('/api/superadmin/societies', methods=['POST'])
@super_admin_required
def sa_create_society():
    d = request.json; db = get_db()
    if not d.get('name'): return jsonify({'error': 'Name required'}), 400
    sid = uid('soc-')
    db.execute('INSERT INTO societies(id,name,address,city,state,pincode) VALUES(?,?,?,?,?,?)',
               (sid, d['name'], d.get('address',''), d.get('city',''), d.get('state',''), d.get('pincode','')))
    # Auto-assign creator as super_admin of new society
    db.execute('INSERT INTO user_society_roles(id,user_id,society_id,role,created_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP)',
               (uid('ur-'), g.user['id'], sid, 'super_admin'))
    db.commit()
    return jsonify({'success': True, 'id': sid})

# Edit society
@app.route('/api/superadmin/societies/<sid>', methods=['PUT'])
@super_admin_required
def sa_edit_society(sid):
    d = request.json; db = get_db()
    db.execute('UPDATE societies SET name=?,address=?,city=?,state=?,pincode=? WHERE id=?',
               (d.get('name'), d.get('address',''), d.get('city',''), d.get('state',''), d.get('pincode',''), sid))
    db.commit()
    return jsonify({'success': True})

# Delete society
@app.route('/api/superadmin/societies/<sid>', methods=['DELETE'])
@super_admin_required
def sa_delete_society(sid):
    db = get_db()
    db.execute('DELETE FROM societies WHERE id=?', (sid,))
    db.execute('DELETE FROM towers WHERE society_id=?', (sid,))
    db.execute('DELETE FROM user_society_roles WHERE society_id=?', (sid,))
    db.commit()
    return jsonify({'success': True})

# Add tower to society
@app.route('/api/superadmin/societies/<sid>/towers', methods=['POST'])
@super_admin_required
def sa_add_tower(sid):
    d = request.json; db = get_db()
    if not d.get('name'): return jsonify({'error': 'Tower name required'}), 400
    tid = uid('twr-')
    floors = int(d.get('floors', 10))
    apts_per_floor = int(d.get('aptsPerFloor', 4))
    db.execute('INSERT INTO towers(id,society_id,name,floors) VALUES(?,?,?,?)', (tid, sid, d['name'], floors))
    # Auto-generate apartments
    for floor in range(1, floors + 1):
        for apt_num in range(1, apts_per_floor + 1):
            unit = f'{floor}0{apt_num}' if apt_num < 10 else f'{floor}{apt_num}'
            db.execute('INSERT INTO apartments(id,tower_id,unit_number,floor) VALUES(?,?,?,?)',
                       (uid('apt-'), tid, unit, floor))
    db.commit()
    return jsonify({'success': True, 'id': tid, 'apartmentsCreated': floors * apts_per_floor})

# Delete tower
@app.route('/api/superadmin/towers/<tid>', methods=['DELETE'])
@super_admin_required
def sa_delete_tower(tid):
    db = get_db()
    db.execute('DELETE FROM apartments WHERE tower_id=?', (tid,))
    db.execute('DELETE FROM towers WHERE id=?', (tid,))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/guard/login-pin', methods=['POST'])
def guard_login_pin():
    pin = (request.json or {}).get('pin', '').strip()
    society_id = (request.json or {}).get('societyId', '').strip()
    if not pin or not society_id:
        return jsonify({'error': 'PIN and society required'}), 400
    db = get_db()
    role_row = dr(db.execute(
        "SELECT usr.*, u.id as user_id, u.name, u.phone FROM user_society_roles usr "
        "JOIN users u ON usr.user_id=u.id "
        "WHERE usr.guard_pin=? AND usr.society_id=? AND usr.role='guard'",
        (pin, society_id)).fetchone())
    if not role_row:
        return jsonify({'error': 'Invalid PIN'}), 401
    # Issue a session token (reuse otp_sessions table — store guard user's phone)
    user = dr(db.execute('SELECT * FROM users WHERE id=?', (role_row['user_id'],)).fetchone())
    sid = uid('otp-')
    db.execute('INSERT INTO otp_sessions VALUES(?,?,?,1,CURRENT_TIMESTAMP)', (sid, user['phone'], pin))
    # Ensure active context is set for this guard
    db.execute('INSERT OR REPLACE INTO user_active_context VALUES(?,?,?)',
               (user['id'], None, society_id))
    db.commit()
    return jsonify({
        'token': sid,
        'user': user,
        'guardName': role_row.get('guard_name') or user.get('name') or 'Guard',
        'societyId': society_id,
    })

# ─── Admin: Guard PIN management (regular admins, not just super_admin) ─────────

@app.route('/api/admin/guards')
@admin_required
def admin_list_guards():
    db = get_db()
    guards = drs(db.execute(
        "SELECT usr.id as role_id, usr.guard_pin, usr.guard_name, u.id as user_id, u.name, u.phone "
        "FROM user_society_roles usr JOIN users u ON usr.user_id=u.id "
        "WHERE usr.society_id=? AND usr.role='guard' ORDER BY usr.guard_name, u.name",
        (g.soc,)).fetchall())
    return jsonify(guards)

@app.route('/api/admin/guards', methods=['POST'])
@admin_required
def admin_create_guard():
    d = request.json or {}; db = get_db()
    name = (d.get('name') or '').strip()
    pin  = (d.get('pin') or '').strip()
    if not name: return jsonify({'error': 'Name required'}), 400
    if not pin or not pin.isdigit() or len(pin) < 4:
        return jsonify({'error': 'PIN must be at least 4 digits'}), 400
    # Check PIN unique within society
    conflict = db.execute(
        "SELECT id FROM user_society_roles WHERE guard_pin=? AND society_id=?",
        (pin, g.soc)).fetchone()
    if conflict: return jsonify({'error': 'PIN already in use by another guard'}), 400
    # Create a synthetic user for this guard (phone = guard-<society>-<pin>)
    synthetic_phone = f"guard-{g.soc[-6:]}-{pin}"
    user = dr(db.execute('SELECT * FROM users WHERE phone=?', (synthetic_phone,)).fetchone())
    if not user:
        user_id = uid('usr-')
        db.execute('INSERT INTO users(id,phone,name) VALUES(?,?,?)', (user_id, synthetic_phone, name))
        user = dr(db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone())
    else:
        db.execute('UPDATE users SET name=? WHERE id=?', (name, user['id']))
    # Assign guard role with PIN
    existing = dr(db.execute(
        "SELECT id FROM user_society_roles WHERE user_id=? AND society_id=? AND role='guard'",
        (user['id'], g.soc)).fetchone())
    if existing:
        db.execute("UPDATE user_society_roles SET guard_pin=?, guard_name=? WHERE id=?",
                   (pin, name, existing['id']))
    else:
        db.execute("INSERT INTO user_society_roles(id,user_id,society_id,role,guard_pin,guard_name,created_at) "
                   "VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                   (uid('ur-'), user['id'], g.soc, 'guard', pin, name))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/guards/<role_id>', methods=['DELETE'])
@admin_required
def admin_delete_guard(role_id):
    db = get_db()
    db.execute("DELETE FROM user_society_roles WHERE id=? AND society_id=? AND role='guard'",
               (role_id, g.soc))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/admin/guards/<role_id>/pin', methods=['PUT'])
@admin_required
def admin_update_guard_pin(role_id):
    d = request.json or {}; db = get_db()
    pin = (d.get('pin') or '').strip()
    if not pin or not pin.isdigit() or len(pin) < 4:
        return jsonify({'error': 'PIN must be at least 4 digits'}), 400
    conflict = db.execute(
        "SELECT id FROM user_society_roles WHERE guard_pin=? AND society_id=? AND id!=?",
        (pin, g.soc, role_id)).fetchone()
    if conflict: return jsonify({'error': 'PIN already in use'}), 400
    db.execute("UPDATE user_society_roles SET guard_pin=? WHERE id=? AND society_id=?",
               (pin, role_id, g.soc))
    db.commit()
    return jsonify({'success': True})


@super_admin_required
def sa_list_staff(sid):
    db = get_db()
    staff = drs(db.execute("""SELECT u.id, u.name, u.phone, usr.role, usr.id as role_id
        FROM user_society_roles usr JOIN users u ON usr.user_id=u.id
        WHERE usr.society_id=? AND usr.role IN ('admin','guard','super_admin')
        ORDER BY usr.role, u.name""", (sid,)).fetchall())
    return jsonify(staff)

# Assign staff (admin or guard) to a society by phone
@app.route('/api/superadmin/societies/<sid>/staff', methods=['POST'])
@super_admin_required
def sa_assign_staff(sid):
    d = request.json; db = get_db()
    phone = d.get('phone'); role = d.get('role')
    if not phone or role not in ('admin', 'guard'): return jsonify({'error': 'Phone and role (admin/guard) required'}), 400
    user = dr(db.execute('SELECT * FROM users WHERE phone=?', (phone,)).fetchone())
    if not user:
        # Create user account
        user_id = uid('usr-')
        db.execute('INSERT INTO users(id,phone,name) VALUES(?,?,?)', (user_id, phone, d.get('name', phone)))
        user = dr(db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone())
    # Check not already assigned
    existing = dr(db.execute('SELECT * FROM user_society_roles WHERE user_id=? AND society_id=?', (user['id'], sid)).fetchone())
    if existing: return jsonify({'error': 'User already has a role in this society'}), 400
    db.execute('INSERT INTO user_society_roles(id,user_id,society_id,role,created_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP)',
               (uid('ur-'), user['id'], sid, role))
    db.commit()
    return jsonify({'success': True, 'userId': user['id']})

# Remove staff from society
@app.route('/api/superadmin/staff/<role_id>', methods=['DELETE'])
@super_admin_required
def sa_remove_staff(role_id):
    db = get_db()
    db.execute('DELETE FROM user_society_roles WHERE id=?', (role_id,))
    db.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    print("GateKeeper API starting on port 3001...")
    app.run(host='0.0.0.0', port=3001, debug=True)
