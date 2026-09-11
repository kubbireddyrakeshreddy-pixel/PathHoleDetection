import requests
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:5000"
IMAGE_PATH = r"C:\Users\RakeshReddy\.gemini\antigravity\brain\0ddd5c69-f80f-44e4-989f-1431348ff196\nalgonda_pothole_test_1788887790494.png"

# Login
login = requests.post(f"{BASE}/api/auth/login/user", json={
    "email": "testcitizen01@test.com",
    "password": "Test1234"
})
resp_json = login.json()
token = resp_json.get("access_token") or resp_json.get("token")
headers = {"Authorization": f"Bearer {token}"}
print("Logged in. Submitting report...")

# Submit report
with open(IMAGE_PATH, "rb") as img:
    files = {"image": ("pothole_nalgonda.png", img, "image/png")}
    data  = {"latitude": "17.0500", "longitude": "79.2667", "address": "Nalgonda Main Road, Telangana"}
    resp  = requests.post(f"{BASE}/api/reports", files=files, data=data, headers=headers, timeout=60)

print(f"Status: {resp.status_code}")
if resp.status_code == 201:
    full = resp.json()
    det  = full.get("detection_result", {})
    rep  = full.get("report", {})
    print("\n====== DETECTION RESULT ======")
    print(f"  Pothole Detected  : {det.get('pothole_detected')}")
    print(f"  Num Potholes      : {det.get('num_potholes')}")
    print(f"  Confidence        : {det.get('max_confidence')}")
    print(f"  Damage Percentage : {det.get('damage_percentage')}")
    print(f"  Report ID         : {rep.get('id')}")
    print(f"  Admin ID assigned : {rep.get('admin_id')}")
    print(f"  Status            : {rep.get('status')}")
    print("==============================")
    if det.get('pothole_detected'):
        print("\nPothole WAS detected! Email alert sent to vinnurakesh2446@gmail.com!")
    else:
        print("\nNo pothole detected in this image.")
else:
    print(f"ERROR: {resp.text[:500]}")
