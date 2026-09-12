"""
app.py — Main Flask application for the Pothole Detection System.

Endpoints
---------
Auth
  POST /api/auth/register/user
  POST /api/auth/register/admin
  POST /api/auth/login/user
  POST /api/auth/login/admin
  GET  /api/auth/me

Reports
  POST /api/reports           — upload image + detect (public)
  GET  /api/reports           — list reports (public = own; admin = all in zone)
  GET  /api/reports/<id>      — single report detail
  PUT  /api/reports/<id>/status — update status (admin only)

Admin
  GET  /api/admin/stats       — dashboard summary stats
  GET  /api/admin/reports     — all reports in admin's zone

Images
  GET  /api/images/<filename> — serve uploaded / annotated images
"""
import os
import uuid
from datetime import datetime, timezone
from functools import wraps

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity, get_jwt,
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import cloudinary
import cloudinary.uploader

import detector
import email_service
from models import db, User, Admin, Report, StatusLog

# ═══════════════════════════════════════════════════════════════════════════
# App Factory
# ═══════════════════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app, supports_credentials=True)

# ── Config ─────────────────────────────────────────────────────────────────
app.config["SECRET_KEY"]             = os.getenv("SECRET_KEY", "dev-secret")
app.config["JWT_SECRET_KEY"]         = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # tokens don't expire (dev)
import ssl
db_url = os.environ.get("DATABASE_URL", "sqlite:///pothole_system.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url

if "mysql" in db_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'ssl': {
                'check_hostname': False,
                'verify_mode': ssl.CERT_NONE
            }
        }
    }
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_TOKEN_LOCATION"] = ["headers", "query_string"]
app.config["JWT_QUERY_STRING_NAME"] = "token"
app.config["UPLOAD_FOLDER"]          = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"]     = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
CONFIDENCE_THRESHOLD                 = float(os.getenv("CONFIDENCE_THRESHOLD", 0.40))
ALLOWED_EXTENSIONS                   = {"jpg", "jpeg", "png", "gif", "webp"}

db.init_app(app)
jwt = JWTManager(app)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

def seed_admins():
    with app.app_context():
        try:
            db.create_all()
            
            a1 = Admin.query.filter_by(email='vinnurakesh2446@gmail.com').first()
            if not a1:
                a1 = Admin(email='vinnurakesh2446@gmail.com', name='Rakesh Reddy', department='Nalgonda Municipal Corp', phone='9059581270', lat_min=16.5, lat_max=17.5, lng_min=78.5, lng_max=79.5)
                db.session.add(a1)
            a1.password_hash = generate_password_hash('Vinnu@123')

            a2 = Admin.query.filter_by(email='srikarreddy465@gmail.com').first()
            if not a2:
                a2 = Admin(email='srikarreddy465@gmail.com', name='Srikar Reddy', department='Chennai Municipal Corp', phone='9059581270', lat_min=12.8, lat_max=13.3, lng_min=80.0, lng_max=80.4)
                db.session.add(a2)
            a2.password_hash = generate_password_hash('Srikar1234')

            a3 = Admin.query.filter_by(email='kubbireddyrakeshreddy@gmail.com').first()
            if not a3:
                a3 = Admin(email='kubbireddyrakeshreddy@gmail.com', name='Rakesh Reddy', department='Super Admin', phone='9059581270', lat_min=None, lat_max=None, lng_min=None, lng_max=None)
                db.session.add(a3)
            a3.password_hash = generate_password_hash('R1234')

            db.session.commit()
        except Exception as e:
            print("[DB] Admin seed error:", e)

def seed_users():
    with app.app_context():
        try:
            u1 = User.query.filter_by(email='vardhantnk@gmail.com').first()
            if not u1:
                u1 = User(name='Harsha Vardhan', username='Harsha123', email='vardhantnk@gmail.com', phone='9059581270')
                db.session.add(u1)
            u1.password_hash = generate_password_hash('harsha123456')

            u2 = User.query.filter_by(email='testuser@gmail.com').first()
            if not u2:
                u2 = User(name='Test Citizen', username='testcitizen', email='testuser@gmail.com', phone='1234567890')
                db.session.add(u2)
            u2.password_hash = generate_password_hash('Test@123')

            db.session.commit()
            print("[DB] Citizen test accounts seeded & passwords synchronized!")
        except Exception as e:
            print("[DB] User seed error:", e)

seed_admins()
seed_users()

# ── Load ML model ──────────────────────────────────────────────────────────
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(os.path.dirname(__file__), "best.pt"))
try:
    detector.load_model(MODEL_PATH)
    MODEL_READY = True
except FileNotFoundError as e:
    print(f"[WARNING] {e}")
    MODEL_READY = False


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
def allowed_file(filename: str) -> bool:
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file) -> str:
    """Save uploaded file and return its absolute path."""
    ext      = secure_filename(file.filename).rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    path     = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)
    
    # Resize image to prevent PyTorch Out-of-Memory (OOM) on Render's 512MB tier
    try:
        import cv2
        img = cv2.imread(path)
        if img is not None:
            h, w = img.shape[:2]
            if max(h, w) > 800:
                scale = 800 / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)))
                cv2.imwrite(path, img)
    except Exception as e:
        print(f"Resize failed: {e}")
        
    return path, filename


def save_annotated(image_bytes: bytes, base_name: str) -> tuple:
    """Save annotated PNG bytes; return (abs_path, filename)."""
    filename = f"ann_{base_name}.png"
    path     = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path, filename


def find_admin_for_location(lat: float, lng: float):
    """Return the first Admin whose zone covers (lat, lng), or None."""
    admins = Admin.query.all()
    for admin in admins:
        if admin.covers(lat, lng):
            return admin
    # Fall back: return any admin (for demo purposes)
    return admins[0] if admins else None


def require_role(role: str):
    """Decorator: require 'user' or 'admin' role in JWT claims."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get("role") != role:
                return jsonify({"error": f"Requires {role} role"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# Auth Routes
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/api/auth/register/user", methods=["POST"])
def register_user():
    data = request.get_json()
    required = ["name", "username", "email", "phone", "password"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409

    user = User(
        name=data["name"], username=data["username"],
        email=data["email"], phone=data["phone"],
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "user", "email": user.email, "name": user.name},
    )
    return jsonify({"token": token, "user": user.to_dict()}), 201


@app.route("/api/auth/register/admin", methods=["POST"])
def register_admin():
    data = request.get_json()
    required = ["name", "email", "phone", "department", "password"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    if Admin.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    admin = Admin(
        name=data["name"], email=data["email"],
        phone=data["phone"], department=data["department"],
        pincode=data.get("pincode"),
        lat_min=data.get("lat_min"), lat_max=data.get("lat_max"),
        lng_min=data.get("lng_min"), lng_max=data.get("lng_max"),
    )
    admin.set_password(data["password"])
    db.session.add(admin)
    db.session.commit()

    token = create_access_token(
        identity=str(admin.id),
        additional_claims={"role": "admin", "email": admin.email, "name": admin.name},
    )
    return jsonify({"token": token, "admin": admin.to_dict()}), 201


@app.route("/api/auth/login/user", methods=["POST"])
def login_user():
    data = request.get_json()
    identifier = data.get("email") or data.get("username")
    if not identifier or not data.get("password"):
        return jsonify({"error": "Email/username and password required"}), 400

    user = User.query.filter(
        (User.email == identifier) | (User.username == identifier)
    ).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": "user", "email": user.email, "name": user.name},
    )
    return jsonify({"token": token, "user": user.to_dict()}), 200


@app.route("/api/auth/login/admin", methods=["POST"])
def login_admin():
    data = request.get_json()
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    admin = Admin.query.filter_by(email=data["email"]).first()
    if not admin or not admin.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(
        identity=str(admin.id),
        additional_claims={"role": "admin", "email": admin.email, "name": admin.name},
    )
    return jsonify({"token": token, "admin": admin.to_dict()}), 200


@app.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    claims  = get_jwt()
    role    = claims.get("role")
    user_id = int(get_jwt_identity())
    if role == "user":
        obj = User.query.get(user_id)
        return jsonify({"role": "user", "data": obj.to_dict() if obj else None})
    else:
        obj = Admin.query.get(user_id)
        return jsonify({"role": "admin", "data": obj.to_dict() if obj else None})


# ═══════════════════════════════════════════════════════════════════════════
# Report Routes
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/api/reports", methods=["POST"])
@require_role("user")
def create_report():
    """Upload an image, run detection, create report, send email."""
    if not MODEL_READY:
        return jsonify({
            "error": "Model not loaded. Place best.pt in the backend/ folder."
        }), 503

    # Validate inputs
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files["image"]
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    lat  = request.form.get("latitude")
    lng  = request.form.get("longitude")
    if not lat or not lng:
        return jsonify({"error": "latitude and longitude are required"}), 400
    try:
        lat, lng = float(lat), float(lng)
    except ValueError:
        return jsonify({"error": "Invalid latitude/longitude values"}), 400

    address = request.form.get("address", "")

    # Save original
    orig_path, orig_filename = save_upload(file)

    # Run detection
    result = detector.detect(orig_path, confidence_threshold=CONFIDENCE_THRESHOLD)

    # Save annotated image
    ann_path, ann_filename = save_annotated(
        result["annotated_bytes"], orig_filename.rsplit(".", 1)[0]
    )
    
    orig_url = orig_filename
    ann_url = ann_filename
    
    if os.getenv("CLOUDINARY_URL"):
        try:
            res1 = cloudinary.uploader.upload(orig_path)
            orig_url = res1.get("secure_url")
            res2 = cloudinary.uploader.upload(ann_path)
            ann_url = res2.get("secure_url")
        except Exception as e:
            print("Cloudinary upload failed:", e)

    # Find responsible admin
    user_id = int(get_jwt_identity())
    admin   = find_admin_for_location(lat, lng)

    # Persist report
    report = Report(
        user_id          = user_id,
        admin_id         = admin.id if admin else None,
        original_image   = orig_url,
        annotated_image  = ann_url,
        latitude         = lat,
        longitude        = lng,
        address          = address,
        confidence_score = result["max_confidence"],
        pothole_detected = result["pothole_detected"],
        num_potholes     = result["num_potholes"],
        damage_percentage= result.get("damage_percentage", 0.0),
        status           = Report.STATUS_REPORTED,
    )
    db.session.add(report)
    db.session.flush()   # get report.id before commit

    # Status log
    log = StatusLog(
        report_id  = report.id,
        status     = Report.STATUS_REPORTED,
        changed_by = "system",
        notes      = "Report submitted by user",
    )
    db.session.add(log)
    db.session.commit()

    # Send email to admin in a background thread (only if pothole detected)
    if result["pothole_detected"] and admin:
        import threading
        import sys
        def send_email_async(rep_id, adm_id, img_path):
            with app.app_context():
                try:
                    rep = Report.query.get(rep_id)
                    adm = Admin.query.get(adm_id)
                    if rep and adm:
                        email_service.send_pothole_alert(rep, adm, img_path)
                        sys.stdout.flush()
                except Exception as e:
                    print(f"[Email Thread Error] {e}", flush=True)
        
        threading.Thread(target=send_email_async, args=(report.id, admin.id, ann_path)).start()

    return jsonify({
        "report":           report.to_dict(include_logs=True),
        "detection_result": {
            "pothole_detected":  result["pothole_detected"],
            "num_potholes":      result["num_potholes"],
            "max_confidence":    result["max_confidence"],
            "damage_percentage": result.get("damage_percentage", 0.0),
            "detections":        result["detections"],
        },
    }), 201


@app.route("/api/reports", methods=["GET"])
@jwt_required()
def list_reports():
    claims  = get_jwt()
    role    = claims.get("role")
    user_id = int(get_jwt_identity())

    if role == "user":
        reports = Report.query.filter_by(user_id=user_id)\
                              .order_by(Report.created_at.desc()).all()
    else:
        admin = Admin.query.get(user_id)
        if admin and admin.lat_min is None:
            reports = Report.query.order_by(Report.created_at.desc()).all()
        else:
            reports = Report.query.filter_by(admin_id=user_id)\
                                  .order_by(Report.created_at.desc()).all()

    return jsonify([r.to_dict() for r in reports])


@app.route("/api/reports/<int:report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id):
    claims  = get_jwt()
    role    = claims.get("role")
    user_id = int(get_jwt_identity())

    report = Report.query.get_or_404(report_id)
    if role == "user" and report.user_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    return jsonify(report.to_dict(include_logs=True))


@app.route("/api/reports/<int:report_id>/status", methods=["PUT"])
@require_role("admin")
def update_status(report_id):
    """Admin updates the repair status of a report."""
    admin_id = int(get_jwt_identity())
    report   = Report.query.get_or_404(report_id)
    data     = request.get_json()
    new_status = data.get("status")

    VALID = [Report.STATUS_REVIEWED, Report.STATUS_IN_PROGRESS, Report.STATUS_REPAIRED]
    if new_status not in VALID:
        return jsonify({"error": f"Invalid status. Must be one of {VALID}"}), 400

    admin = Admin.query.get(admin_id)
    report.status     = new_status
    report.updated_at = datetime.now(timezone.utc)
    if data.get("notes"):
        report.admin_notes = data["notes"]

    log = StatusLog(
        report_id  = report.id,
        status     = new_status,
        changed_by = admin.name if admin else "admin",
        notes      = data.get("notes", ""),
    )
    db.session.add(log)
    db.session.commit()

    # Notify user by email
    email_service.send_status_update(report)

    return jsonify(report.to_dict(include_logs=True))

@app.route("/api/reports/<int:report_id>", methods=["DELETE"])
@require_role("admin")
def delete_report(report_id):
    """Super Admin deletes a report."""
    admin_id = int(get_jwt_identity())
    admin = Admin.query.get(admin_id)
    if admin is None or admin.lat_min is not None:
        return jsonify({"error": "Only Super Admins can delete reports"}), 403
        
    report = Report.query.get_or_404(report_id)
    
    # Delete associated status logs
    StatusLog.query.filter_by(report_id=report.id).delete()
    
    db.session.delete(report)
    db.session.commit()
    
    return jsonify({"message": "Report deleted successfully"}), 200


# ═══════════════════════════════════════════════════════════════════════════
# Admin Dashboard Stats
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/api/admin/stats", methods=["GET"])
@require_role("admin")
def admin_stats():
    admin_id = int(get_jwt_identity())
    admin = Admin.query.get(admin_id)
    if admin and admin.lat_min is None:
        base = Report.query
    else:
        base = Report.query.filter_by(admin_id=admin_id)
        
    return jsonify({
        "total":       base.count(),
        "reported":    base.filter_by(status=Report.STATUS_REPORTED).count(),
        "reviewed":    base.filter_by(status=Report.STATUS_REVIEWED).count(),
        "in_progress": base.filter_by(status=Report.STATUS_IN_PROGRESS).count(),
        "repaired":    base.filter_by(status=Report.STATUS_REPAIRED).count(),
    })


# ═══════════════════════════════════════════════════════════════════════════
# Static image serving
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/api/images/<filename>")
def serve_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ═══════════════════════════════════════════════════════════════════════════
# Serve Frontend SPA
# ═══════════════════════════════════════════════════════════════════════════
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# ═══════════════════════════════════════════════════════════════════════════
# Init DB & Run
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("[DB] Tables created / verified.")
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
