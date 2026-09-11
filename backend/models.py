"""
models.py — SQLAlchemy database models for the Pothole Detection System.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ---------------------------------------------------------------------------
# Public User model
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    username   = db.Column(db.String(80),  nullable=False, unique=True)
    email      = db.Column(db.String(120), nullable=False, unique=True)
    phone      = db.Column(db.String(20),  nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reports    = db.relationship("Report", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "username":   self.username,
            "email":      self.email,
            "phone":      self.phone,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Admin (Government Officer) model
# ---------------------------------------------------------------------------
class Admin(db.Model):
    __tablename__ = "admins"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(120), nullable=False, unique=True)
    phone        = db.Column(db.String(20),  nullable=False)
    department   = db.Column(db.String(120), nullable=False)
    pincode      = db.Column(db.String(20),  nullable=True)   # optional zone
    # Geographic zone: bounding box in decimal degrees
    lat_min      = db.Column(db.Float, nullable=True)
    lat_max      = db.Column(db.Float, nullable=True)
    lng_min      = db.Column(db.Float, nullable=True)
    lng_max      = db.Column(db.Float, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    reports      = db.relationship("Report", backref="admin", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def covers(self, lat: float, lng: float) -> bool:
        """Return True if the given coords fall inside this admin's zone."""
        if self.lat_min is not None and self.lat_max is not None \
                and self.lng_min is not None and self.lng_max is not None:
            return (self.lat_min <= lat <= self.lat_max and
                    self.lng_min <= lng <= self.lng_max)
        return False

    def to_dict(self):
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "phone":      self.phone,
            "department": self.department,
            "pincode":    self.pincode,
            "lat_min":    self.lat_min,
            "lat_max":    self.lat_max,
            "lng_min":    self.lng_min,
            "lng_max":    self.lng_max,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Pothole Report model
# ---------------------------------------------------------------------------
class Report(db.Model):
    __tablename__ = "reports"

    # Status constants
    STATUS_REPORTED    = "reported"
    STATUS_REVIEWED    = "reviewed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_REPAIRED    = "repaired"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    admin_id         = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=True)
    original_image   = db.Column(db.String(256), nullable=False)
    annotated_image  = db.Column(db.String(256), nullable=True)
    latitude         = db.Column(db.Float, nullable=False)
    longitude        = db.Column(db.Float, nullable=False)
    address          = db.Column(db.String(512), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    pothole_detected = db.Column(db.Boolean, default=False)
    num_potholes     = db.Column(db.Integer, default=0)
    damage_percentage= db.Column(db.Float, default=0.0)
    status           = db.Column(db.String(30), default=STATUS_REPORTED)
    admin_notes      = db.Column(db.Text, nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    status_logs      = db.relationship("StatusLog", backref="report", lazy=True,
                                       order_by="StatusLog.timestamp")

    def to_dict(self, include_logs=False):
        data = {
            "id":               self.id,
            "user_id":          self.user_id,
            "user_name":        self.user.name if self.user else None,
            "user_email":       self.user.email if self.user else None,
            "admin_id":         self.admin_id,
            "original_image":   self.original_image,
            "annotated_image":  self.annotated_image,
            "latitude":         self.latitude,
            "longitude":        self.longitude,
            "address":          self.address,
            "confidence_score": self.confidence_score,
            "pothole_detected": self.pothole_detected,
            "num_potholes":     self.num_potholes,
            "damage_percentage":self.damage_percentage,
            "status":           self.status,
            "admin_notes":      self.admin_notes,
            "created_at":       self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at":       self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }
        if include_logs:
            data["status_logs"] = [log.to_dict() for log in self.status_logs]
        return data


# ---------------------------------------------------------------------------
# Status History Log model
# ---------------------------------------------------------------------------
class StatusLog(db.Model):
    __tablename__ = "status_logs"

    id         = db.Column(db.Integer, primary_key=True)
    report_id  = db.Column(db.Integer, db.ForeignKey("reports.id"), nullable=False)
    status     = db.Column(db.String(30), nullable=False)
    changed_by = db.Column(db.String(120), nullable=True)
    notes      = db.Column(db.Text, nullable=True)
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "report_id":  self.report_id,
            "status":     self.status,
            "changed_by": self.changed_by,
            "notes":      self.notes,
            "timestamp":  self.timestamp.isoformat() + "Z",
        }
