import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import init_db, get_conn, uid

init_db()
conn = get_conn(); c = conn.cursor()
for t in ['daily_help_apartments','daily_help','lease_extensions','move_requests','marketplace_posts','delivery_apartments','visitor_entries','visitor_invitations','payments','invoices','bookings','spaces','pets','vehicles','documents','document_requirements','otp_sessions','user_active_context','residents','user_society_roles','users','apartments','towers','societies']:
    c.execute(f'DELETE FROM {t}')

s1, s2 = 'soc-001', 'soc-002'
c.execute("INSERT INTO societies VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)", (s1,'Green Valley Residences','123 Park Avenue','Mumbai','Maharashtra','400001'))
c.execute("INSERT INTO societies VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)", (s2,'Sunrise Heights','456 Lake Road','Pune','Maharashtra','411001'))

t1, t2, t3 = 'twr-001', 'twr-002', 'twr-003'
c.execute("INSERT INTO towers VALUES(?,?,?,?,CURRENT_TIMESTAMP)", (t1,s1,'Tower A',15))
c.execute("INSERT INTO towers VALUES(?,?,?,?,CURRENT_TIMESTAMP)", (t2,s1,'Tower B',12))
c.execute("INSERT INTO towers VALUES(?,?,?,?,CURRENT_TIMESTAMP)", (t3,s2,'Block 1',8))

for tid, prefix, floors in [(t1,'A',5),(t2,'B',5),(t3,'C',3)]:
    for f in range(1, floors+1):
        for u in range(1,5):
            aid = f'apt-{prefix}{f}0{u}'
            c.execute("INSERT INTO apartments VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)", (aid, tid, f'{prefix}-{f}0{u}', f, 2 if f%2 else 3, 1000+f*100))

admin1, admin2 = 'usr-admin-001', 'usr-admin-002'
guard1, guard2 = 'usr-guard-001', 'usr-guard-002'
u1,u2,u3,u4,u5 = 'usr-001','usr-002','usr-003','usr-004','usr-005'
for uid2,ph,nm,em in [(admin1,'9999900001','Admin Sharma','admin@gv.com'),(admin2,'9999900003','Admin Desai','admin@sh.com'),(guard1,'9999900002','Raju Guard',None),(guard2,'9999900004','Mohan Guard',None),(u1,'9876543210','Rahul Mehta','rahul@email.com'),(u2,'9876543211','Priya Patel','priya@email.com'),(u3,'9876543212','Amit Kumar','amit@email.com'),(u4,'9876543213','Sneha Reddy','sneha@email.com'),(u5,'9876543214','Vikram Singh','vikram@email.com')]:
    c.execute("INSERT INTO users VALUES(?,?,?,?,CURRENT_TIMESTAMP)", (uid2,ph,nm,em))

for u,s,r in [(admin1,s1,'admin'),(admin1,s1,'super_admin'),(admin2,s2,'admin'),(guard1,s1,'guard'),(guard2,s2,'guard'),(u1,s1,'resident'),(u2,s1,'resident'),(u3,s1,'resident'),(u4,s1,'resident'),(u1,s2,'resident'),(u5,s2,'resident')]:
    c.execute("INSERT INTO user_society_roles VALUES(?,?,?,?,CURRENT_TIMESTAMP)", (uid('ur-'),u,s,r))

c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-001',u1,'apt-A101',s1,'owner','approved',None,None,None))
c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-002',u2,'apt-A102',s1,'owner','approved',None,None,None))
c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-003',u3,'apt-B101',s1,'tenant','approved',None,'2024-01-01','2025-12-31'))
c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-004',u4,'apt-A201',s1,'family_member','approved',u1,None,None))
c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-005',u1,'apt-C101',s2,'owner','approved',None,None,None))
c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-006',u5,'apt-C102',s2,'owner','approved',None,None,None))
c.execute("INSERT INTO residents VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('res-007',u5,'apt-A301',s1,'tenant','pending',None,'2026-01-01','2026-12-31'))

for u,a,s in [(u1,'apt-A101',s1),(u2,'apt-A102',s1),(u3,'apt-B101',s1),(u4,'apt-A201',s1),(u5,'apt-C102',s2),(admin1,None,s1),(admin2,None,s2),(guard1,None,s1),(guard2,None,s2)]:
    c.execute("INSERT OR REPLACE INTO user_active_context VALUES(?,?,?)", (u,a,s))

c.execute("INSERT INTO vehicles VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('veh-001',u1,'apt-A101',s1,'car','Hyundai','Creta','White','MH01AB1234'))
c.execute("INSERT INTO vehicles VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('veh-002',u2,'apt-A102',s1,'bike','Royal Enfield','Classic 350','Black','MH02CD5678'))
c.execute("INSERT INTO vehicles VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('veh-003',u1,'apt-C101',s2,'car','Maruti','Swift','Red','MH12EF9012'))
c.execute("INSERT INTO pets VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('pet-001',u1,'apt-A101',s1,'dog','Bruno','Golden Retriever',3,1))
c.execute("INSERT INTO pets VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('pet-002',u2,'apt-A102',s1,'cat','Whiskers','Persian',2,1))

c.execute("INSERT INTO spaces VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('spc-001',s1,'Community Hall','Large hall for events','party_hall',100,0,1,500,'08:00','22:00'))
c.execute("INSERT INTO spaces VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('spc-002',s1,'Co-Working Space','10 desks shared','work_area',10,1,10,100,'07:00','21:00'))
c.execute("INSERT INTO spaces VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('spc-003',s1,'Meeting Room A','8 seat meeting room','common_room',8,0,1,200,'09:00','18:00'))
c.execute("INSERT INTO spaces VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('spc-004',s2,'Clubhouse','Sunrise clubhouse','party_hall',50,0,1,300,'09:00','21:00'))
c.execute("INSERT INTO spaces VALUES(?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('spc-005',s2,'Study Room','Quiet study area','work_area',6,1,6,50,'06:00','22:00'))

c.execute("INSERT INTO bookings VALUES(?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('bk-001','spc-001',u1,s1,1,'2026-03-15','10:00','14:00','confirmed',2000))
c.execute("INSERT INTO invoices VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('inv-001','bk-001',u1,s1,2000,'Community Hall - Mar 15','paid'))
c.execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('pay-001','inv-001',u1,s1,2000,'gateway','TXN_MOCK_001','success'))

c.execute("INSERT INTO marketplace_posts VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('mp-001',u1,s1,'sell','Sofa Set 3+1+1','Barely used beige',25000,None,'active'))
c.execute("INSERT INTO marketplace_posts VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('mp-002',u2,s1,'buy','Study Table','Budget under 5000',5000,None,'active'))
c.execute("INSERT INTO marketplace_posts VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('mp-003',u5,s2,'sell','Btwin Cycle','6 months old',8000,None,'active'))

qr1 = 'QR-' + uuid.uuid4().hex[:8].upper()
c.execute("INSERT INTO visitor_invitations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('vinv-001',u1,'apt-A101',s1,'Rohan Gupta','9988776655','guest','Dinner',qr1,'2026-03-03T18:00','2026-03-03T23:00',0,'active'))

for did,si,rt,dt in [('dreq-001',s1,'owner','property_papers'),('dreq-002',s1,'owner','government_id'),('dreq-003',s1,'tenant','rent_agreement'),('dreq-004',s1,'tenant','government_id'),('dreq-005',s1,'family_member','government_id'),('dreq-006',s2,'owner','property_papers'),('dreq-007',s2,'owner','government_id'),('dreq-008',s2,'tenant','rent_agreement'),('dreq-009',s2,'tenant','government_id')]:
    c.execute("INSERT INTO document_requirements VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)", (did,si,rt,dt,1))

c.execute("INSERT INTO daily_help VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('dh-001',s1,'Lakshmi','9111122222','maid','DH-001','QR-DH-001',None,'approved'))
c.execute("INSERT INTO daily_help VALUES(?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)", ('dh-002',s1,'Ramu','9111133333','cook','DH-002','QR-DH-002',None,'pending'))
c.execute("INSERT INTO daily_help_apartments VALUES(?,?,?,?,?)", ('dha-001','dh-001','apt-A101','mon,tue,wed,thu,fri,sat','08:00-10:00'))
c.execute("INSERT INTO daily_help_apartments VALUES(?,?,?,?,?)", ('dha-002','dh-001','apt-A102','mon,wed,fri','10:00-11:00'))

conn.commit(); conn.close()
print('Seed complete!')
print('Logins: 9876543210(Rahul) 9876543211(Priya) 9876543212(Amit) 9999900001(AdminGV) 9999900003(AdminSH) 9999900002(GuardGV) 9999900004(GuardSH)')
print('OTP: 123456')
