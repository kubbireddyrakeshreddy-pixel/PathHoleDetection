# 🚧 RoadSafe Portal — AI-Powered Pothole Detection System

> Detect road potholes using YOLOv11 AI, report them with GPS coordinates, and track government repairs in real time.

---

## 🧱 Project Structure

```
Major_final/
├── model/
│   └── pothole_train.ipynb     ← Kaggle training notebook (run this first!)
├── backend/
│   ├── app.py                  ← Flask REST API (main server)
│   ├── models.py               ← SQLAlchemy DB models
│   ├── detector.py             ← YOLOv11 inference engine
│   ├── email_service.py        ← SendGrid email notifications
│   ├── requirements.txt        ← Python dependencies
│   ├── .env.example            ← Environment config template
│   └── best.pt                 ← ⬅ Place your trained model here!
└── frontend/
    ├── index.html              ← Landing page
    ├── public-login.html       ← Citizen login/register
    ├── admin-login.html        ← Admin login/register
    ├── public-dashboard.html   ← Citizen portal (upload + track)
    ├── admin-dashboard.html    ← Admin portal (manage + update status)
    ├── css/styles.css          ← Global design system
    └── js/
        ├── api.js              ← API client + utilities
        ├── public-dashboard.js ← Citizen portal logic
        └── admin-dashboard.js  ← Admin portal logic
```

---

## 🚀 Quick Start

### Step 1 — Train the Model on Kaggle

1. Go to [https://kaggle.com](https://kaggle.com) and sign in
2. Create a new notebook → upload `model/pothole_train.ipynb`
3. **Settings → Accelerator → GPU T4 x2**
4. Run all cells (takes ~2-4 hours)
5. Download `best.pt` from the **Output** tab
6. Place `best.pt` inside `backend/best.pt`

### Step 2 — Configure Environment

```bash
cd backend
copy .env.example .env
```

Edit `.env` and fill in:
```env
SECRET_KEY=your-strong-random-secret
JWT_SECRET_KEY=another-strong-secret
SENDGRID_API_KEY=SG.your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
```

**Get a free SendGrid API key:**
1. Sign up at [https://sendgrid.com](https://sendgrid.com)
2. Go to Settings → API Keys → Create API Key (Full Access)
3. Paste the key in `.env`

### Step 3 — Install Python Dependencies

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Step 4 — Run the Server

```bash
cd backend
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🌐 Website Pages

| Page | URL | Description |
|------|-----|-------------|
| Landing | `/` | Home page with features overview |
| Citizen Login | `/public-login.html` | Register / login as a citizen |
| Admin Login | `/admin-login.html` | Register / login as a government officer |
| Citizen Dashboard | `/public-dashboard.html` | Upload images, view your reports |
| Admin Dashboard | `/admin-dashboard.html` | Manage reports, update status |

---

## 🔄 System Flow

```
Citizen uploads image + GPS
         ↓
YOLOv11 detects potholes
         ↓
    Pothole detected?
   YES ↓          NO ↓
Report created   Report saved (no alert)
GPS lookup → find admin
Email sent to admin (SendGrid)
         ↓
Admin logs in → sees report on dashboard
Admin clicks: Reviewed → Work in Progress → Road Repaired
         ↓
Each status change → Email sent to citizen
         ↓
Citizen tracks progress in dashboard
```

---

## 📡 API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/user` | Create citizen account |
| POST | `/api/auth/register/admin` | Create admin account |
| POST | `/api/auth/login/user` | Citizen login |
| POST | `/api/auth/login/admin` | Admin login |
| GET  | `/api/auth/me` | Get current user info |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reports` | Upload image + run detection |
| GET  | `/api/reports` | List reports (own for citizen, zone for admin) |
| GET  | `/api/reports/<id>` | Get single report with status history |
| PUT  | `/api/reports/<id>/status` | Update status (admin only) |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/admin/stats` | Dashboard summary stats |

---

## 🤖 Model Details

| Property | Value |
|----------|-------|
| Architecture | YOLOv11-Large |
| Base weights | COCO pretrained |
| Image size | 640×640 |
| Training epochs | 100 (with early stopping) |
| Optimizer | AdamW |
| LR Scheduler | Cosine decay |
| **Target mAP@50** | **>88%** |
| **Target F1** | **>0.88** |
| **Target Precision** | **>90%** |

### Datasets Used
- **RDD2022** — 47,000+ images from 6 countries, multiple road damage types
- **MWPD** — Multi-Weather Pothole Dataset (day/night/rain)
- **Pothole YOLOv8** — 2,000 images with diverse lighting and weather

### Augmentation Pipeline
- Mosaic (4-image tiling), Mixup, Copy-paste
- HSV brightness/saturation shifts (simulates different lighting)
- Night simulation: darkening + blue tint
- Wet simulation: specular highlights + color shift
- CLAHE: contrast-limited adaptive histogram equalization
- Geometric: flip, rotation, shear, perspective

---

## 📧 Email Notifications

### Admin Alert (on pothole detection)
- Sent to: Government officer covering the GPS zone
- Contains: Annotated pothole image (attachment), GPS coordinates, Google Maps link, report details

### Status Update (to citizen)
- Triggered on: Every status change (Reviewed / Work in Progress / Repaired)
- Contains: Current status badge, admin notes, GPS link

---

## 🔒 Security Notes

- Passwords are hashed with Werkzeug (PBKDF2-SHA256)
- All API endpoints (except login/register) require a valid JWT token
- Images are only accessible with a valid JWT token
- CORS is configured to allow frontend access

---

## 📦 Requirements

- Python 3.10+
- Windows / Linux / macOS
- GPU recommended for model training (use Kaggle free GPU)
- ~1 GB RAM minimum for inference (CPU mode)

---

## 📌 Troubleshooting

### `best.pt not found` error
→ Download `best.pt` from your Kaggle notebook Output tab and place it in `backend/best.pt`

### `SENDGRID_API_KEY not set` error  
→ Sign up at sendgrid.com, create an API key, add it to `backend/.env`

### Port 5000 already in use
→ Change port: `python app.py` and edit `app.run(port=5001)` in `app.py`

### Out of memory on Kaggle GPU
→ Reduce `batch=8` in `pothole_train.ipynb` Step 6
