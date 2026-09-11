"""
seed_admin.py — Seeds the database with the default admin account.

Run once:
    python seed_admin.py

The script is safe to run multiple times — it will skip if the email
already exists, so it won't duplicate the admin.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app import app
from models import db, Admin

# ── Default admin credentials ──────────────────────────────────────────────
DEFAULT_ADMIN = {
    "name":       "Rakesh",
    "email":      "vinnurakesh2446@gmail.com",
    "phone":      "8125413278",
    "department": "R&B",
    "pincode":    "508001",
    "password":   "R1234",
    # Geographic zone for pincode 508001 (Nalgonda, Telangana)
    # approx bounding box — can be adjusted later
    "lat_min":    16.80,
    "lat_max":    17.20,
    "lng_min":    79.10,
    "lng_max":    79.50,
}

def seed():
    with app.app_context():
        db.create_all()

        existing = Admin.query.filter_by(email=DEFAULT_ADMIN["email"]).first()
        if existing:
            print(f"[Seed] Admin already exists: {existing.email} — skipping.")
            return

        admin = Admin(
            name       = DEFAULT_ADMIN["name"],
            email      = DEFAULT_ADMIN["email"],
            phone      = DEFAULT_ADMIN["phone"],
            department = DEFAULT_ADMIN["department"],
            pincode    = DEFAULT_ADMIN["pincode"],
            lat_min    = DEFAULT_ADMIN["lat_min"],
            lat_max    = DEFAULT_ADMIN["lat_max"],
            lng_min    = DEFAULT_ADMIN["lng_min"],
            lng_max    = DEFAULT_ADMIN["lng_max"],
        )
        admin.set_password(DEFAULT_ADMIN["password"])
        db.session.add(admin)
        db.session.commit()

        print("=" * 50)
        print("  ✅  Default admin seeded successfully!")
        print("=" * 50)
        print(f"  Name       : {admin.name}")
        print(f"  Email      : {admin.email}")
        print(f"  Phone      : {admin.phone}")
        print(f"  Department : {admin.department}")
        print(f"  Pincode    : {admin.pincode}")
        print(f"  Zone Lat   : {admin.lat_min} → {admin.lat_max}")
        print(f"  Zone Lng   : {admin.lng_min} → {admin.lng_max}")
        print(f"  Password   : {DEFAULT_ADMIN['password']}")
        print("=" * 50)
        print("  You can now login at /admin-login.html")
        print("=" * 50)


if __name__ == "__main__":
    seed()
