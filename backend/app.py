import os, sys, uuid
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import init_db, get_conn, dr, drs, uid

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

@app.route('/')
def index(): return send_from_directory('../frontend', 'resident.html')
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
    pay_id = uid('pay-'); txn = 'TXN_' + uuid.uuid4().hex[:12].upper()
    db.execute('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(pay_id,inv['id'],g.user['id'],g.soc,inv['amount'],'gateway',txn,'success'))
    db.execute("UPDATE invoices SET status='paid' WHERE id=?",(inv['id'],))
    db.execute("UPDATE bookings SET status='confirmed' WHERE id=?",(bk_id,))
    db.commit()
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

@app.route('/api/visitors/invite', methods=['POST'])
@auth_required
def invite_visitor():
    d = request.json; db = get_db()
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    vid = uid('vinv-'); qr = 'QR-' + uuid.uuid4().hex[:8].upper()
    db.execute('INSERT INTO visitor_invitations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(vid,g.user['id'],g.apt,g.soc,d['visitorName'],d.get('visitorPhone'),d.get('visitorType','guest'),d.get('purpose'),qr,d.get('validFrom'),d.get('validTo'),1 if d.get('isRecurring') else 0,'active'))
    db.commit()
    return jsonify({'id':vid,'qrCode':qr})

@app.route('/api/visitors/my-invitations')
@auth_required
def my_invitations():
    return jsonify(drs(get_db().execute('SELECT * FROM visitor_invitations WHERE user_id=? AND society_id=? ORDER BY created_at DESC',(g.user['id'],g.soc or '')).fetchall()))

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
def approve_visitor(vid): get_db().execute("UPDATE visitor_entries SET approval_status='approved' WHERE id=?",(vid,)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/visitors/<vid>/reject', methods=['POST'])
@auth_required
def reject_visitor(vid): get_db().execute("UPDATE visitor_entries SET approval_status='rejected' WHERE id=?",(vid,)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/visitors/delivery/<did>/approve', methods=['POST'])
@auth_required
def approve_delivery(did): get_db().execute("UPDATE delivery_apartments SET approval_status='approved', approved_by=? WHERE id=?",(g.user['id'],did)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/visitors/invitations/<vid>', methods=['DELETE'])
@auth_required
def cancel_invitation(vid): get_db().execute("UPDATE visitor_invitations SET status='cancelled' WHERE id=? AND user_id=?",(vid,g.user['id'])); get_db().commit(); return jsonify({'success':True})

@app.route('/api/marketplace')
@auth_required
def marketplace():
    if not g.soc: return jsonify([])
    return jsonify(drs(get_db().execute("SELECT mp.*, u.name as posted_by FROM marketplace_posts mp JOIN users u ON mp.user_id=u.id WHERE mp.society_id=? AND mp.status='active' ORDER BY mp.created_at DESC",(g.soc,)).fetchall()))

@app.route('/api/marketplace', methods=['POST'])
@auth_required
def create_post():
    d = request.json; db = get_db(); pid = uid('mp-')
    if not g.soc: return jsonify({'error':'No active society'}), 400
    db.execute('INSERT INTO marketplace_posts VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(pid,g.user['id'],g.soc,d.get('postType'),d['title'],d.get('description'),d.get('price'),None,'active')); db.commit()
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

@app.route('/api/move-requests', methods=['POST'])
@auth_required
def create_move():
    d = request.json; db = get_db(); mid = uid('mv-')
    if not g.apt: return jsonify({'error':'No active apartment'}), 400
    db.execute('INSERT INTO move_requests VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)',(mid,g.user['id'],g.apt,g.soc,d.get('moveType'),d.get('tentativeStart'),d.get('tentativeEnd'),'pending',d.get('notes'))); db.commit()
    return jsonify({'success':True,'id':mid})

@app.route('/api/move-requests/my')
@auth_required
def my_moves(): return jsonify(drs(get_db().execute('SELECT * FROM move_requests WHERE user_id=? AND society_id=? ORDER BY created_at DESC',(g.user['id'],g.soc or '')).fetchall()))

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
    return jsonify(drs(db.execute('SELECT a.*, t.name as tower_name FROM apartments a JOIN towers t ON a.tower_id=t.id WHERE t.society_id=?',(g.soc,)).fetchall()))

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
def admin_approve_res(rid): get_db().execute("UPDATE residents SET status='approved' WHERE id=? AND society_id=?",(rid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/residents/<rid>/reject', methods=['POST'])
@admin_required
def admin_reject_res(rid): get_db().execute("UPDATE residents SET status='rejected' WHERE id=? AND society_id=?",(rid,g.soc)); get_db().commit(); return jsonify({'success':True})

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
    return jsonify(drs(get_db().execute("SELECT mr.*, u.name, u.phone, a.unit_number, t.name as tower_name FROM move_requests mr JOIN users u ON mr.user_id=u.id JOIN apartments a ON mr.apartment_id=a.id JOIN towers t ON a.tower_id=t.id WHERE mr.society_id=? ORDER BY mr.created_at DESC",(g.soc,)).fetchall()))

@app.route('/api/admin/move-requests/<mid>/approve', methods=['POST'])
@admin_required
def admin_approve_move(mid): get_db().execute("UPDATE move_requests SET status='approved' WHERE id=? AND society_id=?",(mid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/move-requests/<mid>/reject', methods=['POST'])
@admin_required
def admin_reject_move(mid): get_db().execute("UPDATE move_requests SET status='rejected' WHERE id=? AND society_id=?",(mid,g.soc)); get_db().commit(); return jsonify({'success':True})

@app.route('/api/admin/lease-extensions')
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
    db.execute("INSERT INTO visitor_entries VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,NULL,?,?,CURRENT_TIMESTAMP)",(eid,d.get('invitationId'),d['visitorName'],d.get('visitorPhone'),d.get('visitorType','guest'),d.get('apartmentId'),g.soc,g.user['id'],'pending',d.get('notes')))
    if d.get('invitationId'): db.execute("UPDATE visitor_invitations SET status='used' WHERE id=?",(d['invitationId'],))
    for apt_id in d.get('deliveryApartments',[]):
        db.execute('INSERT INTO delivery_apartments VALUES(?,?,?,?,?)',(uid('da-'),eid,apt_id,'pending',None))
    db.commit()
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

if __name__ == '__main__':
    print("GateKeeper API starting on port 3001...")
    app.run(host='0.0.0.0', port=3001, debug=True)
