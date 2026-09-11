import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

print(f"Testing with User: {GMAIL_USER}")
print(f"Password starts with: {GMAIL_PASSWORD[:4] if GMAIL_PASSWORD else 'None'}")

to_email = "vinnurakesh2446@gmail.com"

msg = MIMEMultipart("related")
msg["From"] = f"RoadSafe Test <{GMAIL_USER}>"
msg["To"] = to_email
msg["Subject"] = "Test Email from RoadSafe"

msg_alt = MIMEMultipart("alternative")
msg.attach(msg_alt)
msg_alt.attach(MIMEText("This is a test email.", "html"))

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        # server.set_debuglevel(1)  # Uncomment for verbose SMTP logging
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
    print(f"Email sent successfully to {to_email}")
except Exception as e:
    print(f"Error sending email: {e}")
