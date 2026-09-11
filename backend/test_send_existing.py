import os
from app import app
from models import db, Report, Admin
import email_service

with app.app_context():
    report = Report.query.get(9)
    admin = Admin.query.get(1)
    
    if not report or not admin:
        print("Report or admin not found")
        exit(1)
        
    ann_path = os.path.join(app.config["UPLOAD_FOLDER"], report.annotated_image)
    
    print(f"Sending email to {admin.email} for report {report.id}...")
    success = email_service.send_pothole_alert(report, admin, ann_path)
    
    print(f"Success: {success}")
