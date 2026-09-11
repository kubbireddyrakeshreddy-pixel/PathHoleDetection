from app import app
from models import db, Admin
from werkzeug.security import generate_password_hash

def seed_admins():
    with app.app_context():
        try:
            db.create_all()
            if not Admin.query.filter_by(email='vinnurakesh2446@gmail.com').first():
                a1 = Admin(email='vinnurakesh2446@gmail.com', password_hash=generate_password_hash('Vinnu@123'),
                           name='Rakesh Reddy', department='Nalgonda Municipal Corp', phone='9059581270',
                           lat_min=16.5, lat_max=17.5, lng_min=78.5, lng_max=79.5)
                db.session.add(a1)
            
            if not Admin.query.filter_by(email='srikarreddy465@gmail.com').first():
                a2 = Admin(email='srikarreddy465@gmail.com', password_hash=generate_password_hash('Srikar1234'),
                           name='Srikar Reddy', department='Chennai Municipal Corp', phone='9059581270',
                           lat_min=12.8, lat_max=13.3, lng_min=80.0, lng_max=80.4)
                db.session.add(a2)
                
            # Super Admin
            if not Admin.query.filter_by(email='kubbireddyrakeshreddy@gmail.com').first():
                a3 = Admin(email='kubbireddyrakeshreddy@gmail.com', password_hash=generate_password_hash('R1234'),
                           name='Rakesh Reddy', department='Super Admin', phone='9059581270',
                           lat_min=None, lat_max=None, lng_min=None, lng_max=None)
                db.session.add(a3)
                
            db.session.commit()
            print("Admins seeded successfully!")
        except Exception as e:
            print("Seed failed:", e)

seed_admins()

if __name__ == "__main__":
    app.run()
