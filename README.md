# MPIS - Missing Person Identification System

## Folder structure
- `face_model.pt` — fine-tuned ResNet-18 face embedding model
- `backend/`
  - `app.py` — Flask server + REST API + MongoDB integration + Email/SMS alerts
  - `face_engine.py` — MTCNN face detection + `face_model.pt` matching
  - `mongo_store.py` — MongoDB connection, counters, indexes, and SQLite migration
  - `notifier.py` — SMTP email and Twilio SMS delivery
  - `requirements.txt` & `.env.example`
- `frontend/` — web UI served directly by Flask
- `Dockerfile`, `Procfile`, `render.yaml` — cloud deployment configuration

## Local Run
```powershell
cd backend
pip install -r requirements.txt
pip install facenet-pytorch --no-deps
python app.py
```
Open `http://localhost:5000` (Staff login default: `admin` / `admin123`, override via `ADMIN_PASSWORD`).

## Cloud Deployment (Render + MongoDB Atlas)
1. **MongoDB Atlas (free)**: Create a free M0 cluster on https://www.mongodb.com/atlas, create a database user, allow network access (`0.0.0.0/0`), and copy the `mongodb+srv://...` connection string.
2. **Email / SMS (optional)**:
   - For Gmail SMTP: turn on 2-Step Verification and generate a 16-character App Password (`SMTP_USER`, `SMTP_PASS`).
   - For SMS: get `TWILIO_SID`, `TWILIO_TOKEN`, and `TWILIO_FROM` from https://www.twilio.com.
3. **Render (Docker)**:
   - On https://render.com, click **New + -> Blueprint** (or **Web Service**), connect `https://github.com/Disha200508/Missing_report`, and it will auto-detect `render.yaml` / `Dockerfile`.
   - Set `MONGO_URI`, `ADMIN_PASSWORD`, and your `SMTP_*` / `TWILIO_*` environment variables, then deploy.
