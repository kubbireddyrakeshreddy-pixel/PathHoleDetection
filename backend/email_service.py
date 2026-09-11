"""
email_service.py — Gmail SMTP-based email notifications.

  send_pothole_alert(report, admin, image_path)
    → sends an HTML email to the government officer with the
      pothole image attached and a Google Maps link.

  send_status_update(report)
    → notifies the public user when the status of their report changes.

SETUP (one-time):
  1. Go to https://myaccount.google.com/apppasswords
  2. Create an App Password for "Mail" (select "Other" → name it "RoadSafe")
  3. Add to your .env file:
       GMAIL_USER=vinnurakesh2446@gmail.com
       GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   (16-char App Password)
"""
import base64
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
FROM_NAME      = os.getenv("SENDGRID_FROM_NAME", "RoadSafe Portal")

# ── status display labels ────────────────────────────────────────────────────
STATUS_LABELS = {
    "reported":    "🔴 Reported",
    "reviewed":    "🟡 Reviewed",
    "in_progress": "🔵 Work in Progress",
    "repaired":    "🟢 Road Repaired",
}


def _send_gmail(to_email: str, subject: str, html_body: str, image_path: str = None) -> bool:
    """Send email via Gmail SMTP with optional inline image."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    GMAIL_USER = os.getenv("GMAIL_USER", "")
    GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "RoadSafe Portal")

    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("[Email] ERROR: GMAIL_USER or GMAIL_APP_PASSWORD not set in .env!")
        return False

    try:
        msg = MIMEMultipart("related")
        msg["From"]    = f"{FROM_NAME} <{GMAIL_USER}>"
        msg["To"]      = to_email
        msg["Subject"] = subject

        # HTML body
        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)
        msg_alt.attach(MIMEText(html_body, "html"))

        # Attach image inline if provided
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_data = f.read()
            img = MIMEImage(img_data)
            img.add_header("Content-ID", "<pothole_img>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(image_path))
            msg.attach(img)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f"[Email] Sent successfully to {to_email}")
        return True

    except Exception as exc:
        print(f"[Email] ERROR: {exc}")
        return False


# ── Public email: alert admin officer ───────────────────────────────────────
def send_pothole_alert(report, admin, annotated_image_path: str) -> bool:
    """
    Send a pothole alert email to the assigned government officer.
    """
    maps_url = (
        f"https://www.google.com/maps?q={report.latitude},{report.longitude}"
    )
    confidence_pct = f"{report.confidence_score * 100:.1f}%" \
        if report.confidence_score else "N/A"
    damage = f"{report.damage_percentage:.1f}%" if report.damage_percentage else "N/A"

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:20px; }}
    .card {{ background:#1e293b; border-radius:16px; padding:32px; max-width:600px; margin:auto;
             border:1px solid #334155; box-shadow:0 4px 32px rgba(0,0,0,0.5); }}
    h2 {{ color:#f97316; margin-top:0; }}
    .badge {{ display:inline-block; background:#dc2626; color:white;
              padding:4px 14px; border-radius:20px; font-weight:700; font-size:13px; }}
    .info-row {{ display:flex; justify-content:space-between; padding:10px 0;
                 border-bottom:1px solid #334155; }}
    .info-label {{ color:#94a3b8; font-size:13px; }}
    .info-value {{ color:#f1f5f9; font-weight:600; }}
    .map-btn {{ display:inline-block; margin-top:20px; background:#f97316; color:white;
                text-decoration:none; padding:12px 28px; border-radius:10px;
                font-weight:700; font-size:15px; }}
    .footer {{ margin-top:24px; color:#64748b; font-size:12px; text-align:center; }}
    img {{ max-width:100%; border-radius:10px; margin-top:20px; border:2px solid #f97316; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>🚧 Pothole Detected — Action Required</h2>
    <span class="badge">DAMAGED ROAD</span>
    <div style="margin-top:20px;">
      <div class="info-row">
        <span class="info-label">Report ID</span>
        <span class="info-value">#{report.id}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Reported By</span>
        <span class="info-value">{report.user.name} ({report.user.email})</span>
      </div>
      <div class="info-row">
        <span class="info-label">Location</span>
        <span class="info-value">Lat {report.latitude:.5f}, Lng {report.longitude:.5f}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Address</span>
        <span class="info-value">{report.address or 'Not provided'}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Detection Confidence</span>
        <span class="info-value">{confidence_pct}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Potholes Detected</span>
        <span class="info-value">{report.num_potholes}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Road Damage</span>
        <span class="info-value">{damage} of road area damaged</span>
      </div>
      <div class="info-row">
        <span class="info-label">Date &amp; Time</span>
        <span class="info-value">{report.created_at.strftime('%d %b %Y, %H:%M UTC')}</span>
      </div>
    </div>
    <a href="{maps_url}" class="map-btn">📍 View on Google Maps</a>
    <br><br>
    <p style="color:#94a3b8; font-size:14px;">Annotated pothole image is attached below.</p>
    <img src="cid:pothole_img" alt="Pothole Detection Image">
    <div class="footer">
      RoadSafe Portal — This is an automated notification.<br>
      Please log in to your dashboard to update the status.
    </div>
  </div>
</body>
</html>
"""
    subject = f"🚧 Pothole Alert — Report #{report.id} | Lat:{report.latitude:.4f} Lng:{report.longitude:.4f}"
    return _send_gmail(admin.email, subject, html_body, annotated_image_path)


# ── Status update email: notify the public user ─────────────────────────────
def send_status_update(report) -> bool:
    """
    Notify the user that their report status has changed.
    """
    maps_url = (
        f"https://www.google.com/maps?q={report.latitude},{report.longitude}"
    )
    status_label = STATUS_LABELS.get(report.status, report.status)
    color_map = {
        "reported":    "#dc2626",
        "reviewed":    "#d97706",
        "in_progress": "#2563eb",
        "repaired":    "#16a34a",
    }
    badge_color = color_map.get(report.status, "#6b7280")

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:20px; }}
    .card {{ background:#1e293b; border-radius:16px; padding:32px; max-width:600px; margin:auto;
             border:1px solid #334155; box-shadow:0 4px 32px rgba(0,0,0,0.5); }}
    h2 {{ color:#38bdf8; margin-top:0; }}
    .badge {{ display:inline-block; background:{badge_color}; color:white;
              padding:6px 18px; border-radius:20px; font-weight:700; font-size:15px; }}
    .info-row {{ display:flex; justify-content:space-between; padding:10px 0;
                 border-bottom:1px solid #334155; }}
    .info-label {{ color:#94a3b8; font-size:13px; }}
    .info-value {{ color:#f1f5f9; font-weight:600; }}
    .btn {{ display:inline-block; margin-top:20px; background:#38bdf8; color:#0f172a;
            text-decoration:none; padding:12px 28px; border-radius:10px;
            font-weight:700; font-size:15px; }}
    .footer {{ margin-top:24px; color:#64748b; font-size:12px; text-align:center; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>📋 Your Report Status Updated</h2>
    <span class="badge">{status_label}</span>
    <div style="margin-top:20px;">
      <div class="info-row">
        <span class="info-label">Report ID</span>
        <span class="info-value">#{report.id}</span>
      </div>
      <div class="info-row">
        <span class="info-label">New Status</span>
        <span class="info-value">{status_label}</span>
      </div>
      <div class="info-row">
        <span class="info-label">Location</span>
        <span class="info-value">Lat {report.latitude:.5f}, Lng {report.longitude:.5f}</span>
      </div>
      {"<div class='info-row'><span class='info-label'>Admin Notes</span><span class='info-value'>" + report.admin_notes + "</span></div>" if report.admin_notes else ""}
    </div>
    <a href="{maps_url}" class="btn">📍 View Location</a>
    <div class="footer">
      RoadSafe Portal — Track your report anytime by logging into your dashboard.<br>
      This is an automated notification.
    </div>
  </div>
</body>
</html>
"""
    subject = f"📋 Report #{report.id} Status: {status_label}"
    return _send_gmail(report.user.email, subject, html_body)
