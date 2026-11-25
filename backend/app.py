"""
Missing Person Identification System (MPIS) - Flask backend with MongoDB.
Run:  python app.py      then open  http://localhost:5000
Env:  MONGO_URI (default: mongodb://localhost:27017), MONGO_DB (default: mpis)
"""
import os, re, json, uuid, datetime, traceback, logging
from functools import wraps

import numpy as np
from bson.binary import Binary
from flask import Flask, Response, request, jsonify, session, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash
from PIL import Image
from pymongo.errors import DuplicateKeyError, PyMongoError

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from mongo_store import get_mongo_db, init_mongo, next_id, clean_doc, format_code
from notifier import send_sms, send_email

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(HERE, "uploads")
DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(HERE, "data")
MISSING_DIR = os.path.join(DATA_DIR, "missing_persons")
SIGHTING_DIR = os.path.join(DATA_DIR, "sightings")
SQLITE_PATH = os.path.join(HERE, "mpis.db")
FRONTEND_DIR = os.path.join(HERE, "..", "frontend")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MISSING_DIR, exist_ok=True)
os.makedirs(SIGHTING_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-in-production")

CASE_STATUSES = ["Active", "Under Investigation", "Probable Match Found", "Verified", "Closed"]
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}

# ---------------------------------------------------------------- face engine (lazy)
engine = None
def get_engine():
    global engine
    if engine is None:
        from face_engine import FaceEngine
        engine = FaceEngine()
    return engine

# ---------------------------------------------------------------- database (MongoDB)
_initialized = False

def db():
    global _initialized
    if not _initialized:
        init_db()
    return get_mongo_db()

def init_db():
    global _initialized
    init_mongo(SQLITE_PATH)
    _initialized = True

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(case_id, event, actor="system"):
    d = db()
    d.history.insert_one({
        "id": next_id(d, "history"),
        "case_id": int(case_id),
        "event": event,
        "actor": actor,
        "created_at": now(),
    })

# ---------------------------------------------------------------- helpers
def err(msg, code=400):
    return jsonify({"error": msg}), code

def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if session.get("user") is None:
            return err("Login required", 401)
        return f(*a, **kw)
    return wrapper

def clean(v, n=300):
    return (v or "").strip()[:n]

def save_photo(file_storage, subdir="missing_persons"):
    """Validate + re-encode as JPEG (also strips EXIF/GPS metadata) into the category folder. Returns relative path."""
    if not file_storage or not file_storage.filename:
        raise ValueError("A photo is required")
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Photo must be JPG, PNG or WEBP")
    try:
        img = Image.open(file_storage.stream)
        img.load()
        img = img.convert("RGB")
    except Exception:
        raise ValueError("That file is not a valid image")
    img.thumbnail((1600, 1600))
    target_dir = MISSING_DIR if subdir == "missing_persons" else SIGHTING_DIR
    os.makedirs(target_dir, exist_ok=True)
    filename = uuid.uuid4().hex + ".jpg"
    img.save(os.path.join(target_dir, filename), "JPEG", quality=90)
    return f"{subdir}/{filename}"

def resolve_photo_path(photo_ref):
    """Resolve a stored photo reference safely across missing_persons, sightings, or legacy uploads."""
    norm = (photo_ref or "").replace("\\", "/").lstrip("/")
    if norm.startswith("missing_persons/"):
        return MISSING_DIR, os.path.basename(norm)
    if norm.startswith("sightings/"):
        return SIGHTING_DIR, os.path.basename(norm)
    return UPLOAD_DIR, os.path.basename(norm)

def save_record_json(kind, record_id, payload):
    """Persist structured JSON record inside the separate missing_persons or sightings folder."""
    try:
        target_dir = MISSING_DIR if kind == "case" else SIGHTING_DIR
        prefix = "case" if kind == "case" else "sighting"
        os.makedirs(target_dir, exist_ok=True)
        clean_payload = clean_doc(payload)
        file_stem = clean_payload.get("code") or f"{prefix}_{record_id}"
        with open(os.path.join(target_dir, f"{file_stem}.json"), "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)
    except Exception as e:
        print(f"[warn] Failed to write record JSON file: {e}")

def read_photo_bytes(photo_ref):
    folder, fname = resolve_photo_path(photo_ref)
    with open(os.path.join(folder, fname), "rb") as f:
        return Binary(f.read())

def to_vec(vec):   return np.asarray(vec, dtype="float32").tolist()
def from_vec(arr): return np.asarray(arr, dtype="float32")

def embed_photo(photo_ref):
    from face_engine import NoFaceError
    folder, fname = resolve_photo_path(photo_ref)
    full_path = os.path.join(folder, fname)
    try:
        return get_engine().embed(full_path)
    except NoFaceError:
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass
        raise ValueError("No face could be detected in that photo. Please upload a clearer, front-facing photo.")
    except Exception as e:
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError:
                pass
        raise RuntimeError(f"Face processing error: {e}")

def notify(match_id, case_doc, message, subject=None):
    """Send SMS (Twilio) and Email (SMTP) alerts and record delivery status in MongoDB."""
    d = db()
    c_code = case_doc.get("code") or f"#{case_doc['id']}"
    mail_subject = subject or f"MPIS Alert: Verified match for case {c_code} ({case_doc.get('name', '')})"
    targets = []
    if case_doc.get("contact_phone"): targets.append(("SMS", case_doc["contact_phone"]))
    if case_doc.get("contact_email"): targets.append(("Email", case_doc["contact_email"]))
    results = []
    for channel, recipient in targets:
        if channel == "SMS":
            status, error = send_sms(recipient, message)
        else:
            status, error = send_email(recipient, mail_subject, message)
        doc = {
            "id": next_id(d, "notifications"),
            "match_id": int(match_id),
            "channel": channel,
            "recipient": recipient,
            "message": message,
            "status": status,
            "error": error,
            "created_at": now(),
        }
        d.notifications.insert_one(doc)
        results.append({"channel": channel, "recipient": recipient, "status": status, "error": error})
        print(f"[notify:{channel}:{status}] -> {recipient}: {message}" + (f" ({error})" if error else ""))
    return results

def create_matches(case_id=None, sighting_id=None):
    """Compare a new case against all sightings (or a new sighting against all non-closed cases)."""
    d, eng = db(), get_engine()
    created = 0
    if case_id is not None:
        base_doc = d.missing_persons.find_one({"id": int(case_id)}, {"embedding": 1, "code": 1})
        if not base_doc or not base_doc.get("embedding"):
            return 0
        base = from_vec(base_doc["embedding"])
        others = list(d.sightings.find({"embedding": {"$exists": True, "$ne": None}}, {"id": 1, "code": 1, "embedding": 1}))
    else:
        base_doc = d.sightings.find_one({"id": int(sighting_id)}, {"embedding": 1, "code": 1})
        if not base_doc or not base_doc.get("embedding"):
            return 0
        base = from_vec(base_doc["embedding"])
        others = list(d.missing_persons.find({"status": {"$ne": "Closed"}, "embedding": {"$exists": True, "$ne": None}}, {"id": 1, "code": 1, "embedding": 1}))

    for o in others:
        if not o.get("embedding"):
            continue
        dist = eng.distance(base, from_vec(o["embedding"]))
        if dist < eng.threshold:
            if case_id is not None:
                c_id, s_id = int(case_id), int(o["id"])
                s_code = o.get("code") or f"#{s_id}"
            else:
                c_id, s_id = int(o["id"]), int(sighting_id)
                s_code = base_doc.get("code") or f"#{s_id}"
            if d.matches.find_one({"case_id": c_id, "sighting_id": s_id}, {"_id": 1}):
                continue
            sc = eng.score(dist)
            try:
                d.matches.insert_one({
                    "id": next_id(d, "matches"),
                    "case_id": c_id,
                    "sighting_id": s_id,
                    "distance": float(dist),
                    "score": int(sc),
                    "status": "pending",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "created_at": now(),
                })
            except DuplicateKeyError:
                continue
            created += 1
            log(c_id, f"Probable match flagged with sighting {s_code} ({sc}% confidence)")
            d.missing_persons.update_one(
                {"id": c_id, "status": {"$in": ["Active", "Under Investigation"]}},
                {"$set": {"status": "Probable Match Found", "updated_at": now()}},
            )
    return created

# ---------------------------------------------------------------- public API
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.get("/api/health")
def health():
    db_ok = False
    db_error = None
    try:
        d = db()
        d.command("ping")
        db_ok = True
    except Exception as e:
        db_error = str(e)

    ai_ok = False
    ai_error = None
    ai_model = None
    try:
        eng = get_engine()
        ai_model = type(eng.model).__name__
        ai_ok = True
    except Exception as e:
        ai_error = str(e)

    is_cloud = bool(os.environ.get("RENDER") or os.environ.get("PORT"))
    status_code = 200 if (db_ok and ai_ok) else (503 if not db_ok else 200)
    return jsonify({
        "status": "healthy" if db_ok and ai_ok else ("degraded" if db_ok else "database_disconnected"),
        "mongodb": {
            "connected": db_ok,
            "uri_set": bool(os.environ.get("MONGO_URI")),
            "error": db_error,
        },
        "ai_engine": {
            "ready": ai_ok,
            "model": ai_model,
            "error": ai_error,
        },
        "environment": "cloud" if is_cloud else "local",
        "timestamp": now(),
    }), status_code

@app.post("/api/cases")
def register_case():
    f = request.form
    name = clean(f.get("name"), 100)
    if not name: return err("Name is required")
    age = None
    if f.get("age"):
        try:
            age = int(f["age"])
            assert 0 <= age <= 120
        except Exception:
            return err("Age must be a number between 0 and 120")
    phone = clean(f.get("contact_phone"), 20)
    email = clean(f.get("contact_email"), 120)
    if not phone and not email:
        return err("Please give a phone number or email so we can contact you if a match is verified")
    if phone and not re.fullmatch(r"[+\d][\d\s\-]{6,18}", phone): return err("Phone number looks invalid")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): return err("Email looks invalid")
    try:
        photo = save_photo(request.files.get("photo"), "missing_persons")
        emb = embed_photo(photo)
        photo_bytes = read_photo_bytes(photo)
    except (ValueError, RuntimeError) as e:
        return err(str(e))
    d = db()
    case_id = next_id(d, "missing_persons")
    ts = now()
    case_code = format_code("missing_person", case_id, ts)
    doc = {
        "id": case_id,
        "code": case_code,
        "name": name,
        "age": age,
        "gender": clean(f.get("gender"), 20),
        "last_seen_location": clean(f.get("last_seen_location")),
        "date_missing": clean(f.get("date_missing"), 20),
        "marks": clean(f.get("marks"), 500),
        "contact_name": clean(f.get("contact_name"), 100),
        "contact_phone": phone,
        "contact_email": email,
        "photo": photo,
        "photo_bytes": photo_bytes,
        "embedding": to_vec(emb),
        "status": "Active",
        "created_at": ts,
        "updated_at": ts,
    }
    d.missing_persons.insert_one(doc)
    log(case_id, f"Case {case_code} registered")
    try:
        create_matches(case_id=case_id)
    except Exception as e:
        print(f"[warn] Match scanning encountered an issue: {e}")
    latest = d.missing_persons.find_one({"id": case_id})
    if latest:
        save_record_json("case", case_id, latest)
    # Privacy: public users are NOT told whether a match exists - only authorised staff review matches.
    return jsonify({"case_id": case_code, "numeric_id": case_id,
                    "message": "Case registered. Keep your Case ID to track its status."}), 201

@app.post("/api/sightings")
def report_sighting():
    f = request.form
    location = clean(f.get("location"))
    if not location: return err("Please tell us where the person was seen")
    try:
        photo = save_photo(request.files.get("photo"), "sightings")
        emb = embed_photo(photo)
        photo_bytes = read_photo_bytes(photo)
    except (ValueError, RuntimeError) as e:
        return err(str(e))
    d = db()
    sighting_id = next_id(d, "sightings")
    ts = now()
    sighting_code = format_code("sighting", sighting_id, ts)
    doc = {
        "id": sighting_id,
        "code": sighting_code,
        "location": location,
        "description": clean(f.get("description"), 800),
        "reporter_name": clean(f.get("reporter_name"), 100),
        "reporter_contact": clean(f.get("reporter_contact"), 120),
        "photo": photo,
        "photo_bytes": photo_bytes,
        "embedding": to_vec(emb),
        "created_at": ts,
    }
    d.sightings.insert_one(doc)
    save_record_json("sighting", sighting_id, doc)
    try:
        create_matches(sighting_id=sighting_id)
    except Exception as e:
        print(f"[warn] Match scanning encountered an issue: {e}")
    for m in d.matches.find({"sighting_id": sighting_id}, {"case_id": 1}):
        crow = d.missing_persons.find_one({"id": m["case_id"]})
        if crow:
            save_record_json("case", m["case_id"], crow)
    return jsonify({"sighting_id": sighting_code, "numeric_id": sighting_id,
                    "message": "Thank you. Your report was submitted and will be reviewed by authorised staff."}), 201

@app.get("/api/cases/<case_ref>/status")
def case_status(case_ref):
    ref = clean(case_ref, 40).upper()
    flt = {"id": int(ref)} if ref.isdigit() else {"code": ref}
    r = db().missing_persons.find_one(flt, {"_id": 0, "id": 1, "code": 1, "status": 1, "updated_at": 1})
    if not r: return err("No case found with that ID", 404)
    return jsonify({
        "id": r.get("code") or str(r["id"]),
        "numeric_id": r["id"],
        "status": r["status"],
        "updated_at": r["updated_at"],
    })   # status only - no personal data

@app.get("/api/stats")
def stats():
    d = db()
    return jsonify({
        "cases": d.missing_persons.count_documents({}),
        "sightings": d.sightings.count_documents({}),
        "verified": d.missing_persons.count_documents({"status": {"$in": ["Verified", "Closed"]}}),
    })

@app.get("/api/next-ids")
def next_ids():
    """Return the next preview IDs for missing person and sighting forms."""
    d = db()
    c_doc = d.counters.find_one({"_id": "missing_persons"}) or {}
    s_doc = d.counters.find_one({"_id": "sightings"}) or {}
    ts = now()
    return jsonify({
        "case_id": format_code("missing_person", int(c_doc.get("seq", 0)) + 1, ts),
        "sighting_id": format_code("sighting", int(s_doc.get("seq", 0)) + 1, ts),
    })

# ---------------------------------------------------------------- auth
@app.post("/api/login")
def login():
    j = request.get_json(silent=True) or {}
    u = db().users.find_one({"username": clean(j.get("username"), 50)})
    if not u or not check_password_hash(u["password_hash"], j.get("password") or ""):
        return err("Wrong username or password", 401)
    session["user"] = u["username"]
    return jsonify({"user": u["username"]})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
def me():
    return jsonify({"user": session.get("user")})

# ---------------------------------------------------------------- admin API
@app.get("/api/admin/overview")
@admin_required
def overview():
    d = db()
    by_status = {s: 0 for s in CASE_STATUSES}
    for r in d.missing_persons.aggregate([{"$group": {"_id": "$status", "c": {"$sum": 1}}}]):
        if r["_id"] in by_status:
            by_status[r["_id"]] = r["c"]
    pending = d.matches.count_documents({"status": "pending"})
    return jsonify({
        "by_status": by_status,
        "pending_matches": pending,
        "sightings": d.sightings.count_documents({}),
    })

@app.get("/api/admin/cases")
@admin_required
def admin_cases():
    q, status = clean(request.args.get("q"), 100), clean(request.args.get("status"), 30)
    flt = {}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        ors = [{"name": rx}, {"last_seen_location": rx}, {"code": rx}]
        if q.isdigit():
            ors.append({"id": int(q)})
        flt["$or"] = ors
    if status:
        flt["status"] = status
    rows = db().missing_persons.find(flt, {"_id": 0, "embedding": 0, "photo_bytes": 0}).sort("id", -1).limit(300)
    return jsonify(list(rows))

@app.get("/api/admin/cases/<int:case_id>")
@admin_required
def admin_case(case_id):
    d = db()
    r = d.missing_persons.find_one({"id": case_id}, {"_id": 0, "embedding": 0, "photo_bytes": 0})
    if not r: return err("Not found", 404)
    hist = list(d.history.find({"case_id": case_id}, {"_id": 0, "event": 1, "actor": 1, "created_at": 1}).sort("id", 1))
    return jsonify({"case": r, "history": hist})

@app.patch("/api/admin/cases/<int:case_id>/status")
@admin_required
def set_status(case_id):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in CASE_STATUSES: return err("Invalid status")
    d = db()
    res = d.missing_persons.update_one({"id": case_id}, {"$set": {"status": status, "updated_at": now()}})
    if not res.matched_count: return err("Not found", 404)
    log(case_id, f"Status changed to {status}", session["user"])
    save_record_json("case", case_id, d.missing_persons.find_one({"id": case_id}))
    return jsonify({"ok": True})

@app.get("/api/admin/matches")
@admin_required
def admin_matches():
    d = db()
    status = clean(request.args.get("status"), 20) or "pending"
    m_rows = list(d.matches.find({"status": status}, {"_id": 0}).sort([("score", -1), ("id", -1)]).limit(200))
    if not m_rows:
        return jsonify([])
    case_ids = list({m["case_id"] for m in m_rows})
    sighting_ids = list({m["sighting_id"] for m in m_rows})
    cases = {c["id"]: c for c in d.missing_persons.find({"id": {"$in": case_ids}}, {"_id": 0, "embedding": 0, "photo_bytes": 0})}
    sightings = {s["id"]: s for s in d.sightings.find({"id": {"$in": sighting_ids}}, {"_id": 0, "embedding": 0, "photo_bytes": 0})}
    out = []
    for m in m_rows:
        c = cases.get(m["case_id"])
        s = sightings.get(m["sighting_id"])
        if not c or not s:
            continue
        out.append({
            "id": m["id"], "score": m["score"], "distance": m["distance"], "status": m["status"],
            "created_at": m["created_at"], "reviewed_by": m.get("reviewed_by"), "reviewed_at": m.get("reviewed_at"),
            "case_id": c["id"], "case_code": c.get("code") or f"#{c['id']}", "name": c["name"], "age": c.get("age"), "gender": c.get("gender"),
            "last_seen_location": c.get("last_seen_location"), "case_photo": c["photo"],
            "sighting_id": s["id"], "sighting_code": s.get("code") or f"#{s['id']}", "sighting_location": s["location"], "description": s.get("description"),
            "seen_at": s["created_at"], "sighting_photo": s["photo"],
        })
    return jsonify(out)

@app.get("/api/admin/matches/<int:mid>")
@admin_required
def admin_match_detail(mid):
    """Full combined report for a match: match metadata, complete missing person case, sighting, history, and sent alerts."""
    d = db()
    m = d.matches.find_one({"id": mid}, {"_id": 0})
    if not m: return err("Match not found", 404)
    c = d.missing_persons.find_one({"id": m["case_id"]}, {"_id": 0, "embedding": 0, "photo_bytes": 0})
    s = d.sightings.find_one({"id": m["sighting_id"]}, {"_id": 0, "embedding": 0, "photo_bytes": 0})
    hist = list(d.history.find({"case_id": m["case_id"]}, {"_id": 0, "event": 1, "actor": 1, "created_at": 1}).sort("id", 1))
    notifs = list(d.notifications.find({"match_id": mid}, {"_id": 0}).sort("id", -1))
    return jsonify({"match": m, "case": c, "sighting": s, "history": hist, "notifications": notifs})

@app.post("/api/admin/matches/<int:mid>/<action>")
@admin_required
def review_match(mid, action):
    if action not in ("verify", "reject", "reopen"): return err("Invalid action")
    d = db()
    m = d.matches.find_one({"id": mid})
    if not m: return err("Not found", 404)
    case = d.missing_persons.find_one({"id": m["case_id"]})
    sight = d.sightings.find_one({"id": m["sighting_id"]}, {"code": 1})
    c_code = case.get("code") or f"#{case['id']}"
    s_code = (sight or {}).get("code") or f"#{m['sighting_id']}"
    ts = now()
    if action == "verify":
        was_verified = (m["status"] == "verified")
        d.matches.update_one({"id": mid}, {"$set": {"status": "verified", "reviewed_by": session["user"], "reviewed_at": ts}})
        d.missing_persons.update_one({"id": case["id"]}, {"$set": {"status": "Verified", "updated_at": ts}})
        log(case["id"], f"Match with sighting {s_code} VERIFIED", session["user"])
        if not was_verified:
            notify(mid, case, f"MPIS update for case {c_code} ({case['name']}): a possible sighting has been verified "
                              f"by our team. An officer will contact you shortly.")
    elif action == "reject":
        d.matches.update_one({"id": mid}, {"$set": {"status": "rejected", "reviewed_by": session["user"], "reviewed_at": ts}})
        log(case["id"], f"Match with sighting {s_code} rejected", session["user"])
        has_verified = d.matches.find_one({"case_id": case["id"], "status": "verified"})
        has_pending = d.matches.find_one({"case_id": case["id"], "status": "pending"})
        if not has_verified:
            next_status = "Probable Match Found" if has_pending else "Active"
            d.missing_persons.update_one({"id": case["id"]}, {"$set": {"status": next_status, "updated_at": ts}})
    else:
        d.matches.update_one({"id": mid}, {"$set": {"status": "pending", "reviewed_by": None, "reviewed_at": None}})
        log(case["id"], f"Match with sighting {s_code} reopened for review", session["user"])
        has_verified = d.matches.find_one({"case_id": case["id"], "status": "verified"})
        if not has_verified and case["status"] in ("Active", "Verified"):
            d.missing_persons.update_one({"id": case["id"]}, {"$set": {"status": "Probable Match Found", "updated_at": ts}})
    save_record_json("case", case["id"], d.missing_persons.find_one({"id": case["id"]}))
    return jsonify({"ok": True})

@app.post("/api/admin/matches/<int:mid>/notify")
@admin_required
def resend_match_alert(mid):
    """Allow staff to resend SMS/Email alert for a verified match."""
    d = db()
    m = d.matches.find_one({"id": mid})
    if not m: return err("Not found", 404)
    case = d.missing_persons.find_one({"id": m["case_id"]})
    if not case: return err("Case not found", 404)
    c_code = case.get("code") or f"#{case['id']}"
    results = notify(
        mid,
        case,
        f"MPIS update for case {c_code} ({case['name']}): a possible sighting has been verified "
        f"by our team. An officer will contact you shortly.",
    )
    log(case["id"], f"Family alert resent for match #{mid}", session["user"])
    return jsonify({"ok": True, "results": results})

@app.get("/api/admin/sightings")
@admin_required
def admin_sightings():
    rows = db().sightings.find({}, {"_id": 0, "embedding": 0, "photo_bytes": 0}).sort("id", -1).limit(200)
    return jsonify(list(rows))

@app.get("/api/admin/notifications")
@admin_required
def admin_notifications():
    d = db()
    rows = list(d.notifications.find({}, {"_id": 0}).sort("id", -1).limit(100))
    match_ids = list({n["match_id"] for n in rows if n.get("match_id") is not None})
    matches = {m["id"]: m for m in d.matches.find({"id": {"$in": match_ids}}, {"_id": 0})} if match_ids else {}
    case_ids = list({m["case_id"] for m in matches.values()})
    sighting_ids = list({m["sighting_id"] for m in matches.values()})
    cases = {c["id"]: c for c in d.missing_persons.find({"id": {"$in": case_ids}}, {"_id": 0, "id": 1, "code": 1, "name": 1, "status": 1})} if case_ids else {}
    sightings = {s["id"]: s for s in d.sightings.find({"id": {"$in": sighting_ids}}, {"_id": 0, "id": 1, "code": 1, "location": 1})} if sighting_ids else {}
    for n in rows:
        m = matches.get(n.get("match_id"))
        if m:
            c = cases.get(m["case_id"], {})
            s = sightings.get(m["sighting_id"], {})
            n["case_id"] = m["case_id"]
            n["case_code"] = c.get("code") or f"#{m['case_id']}"
            n["sighting_id"] = m["sighting_id"]
            n["sighting_code"] = s.get("code") or f"#{m['sighting_id']}"
            n["score"] = m["score"]
            n["match_status"] = m["status"]
            n["case_name"] = c.get("name")
            n["case_status"] = c.get("status")
            n["sighting_location"] = s.get("location")
    return jsonify(rows)

@app.get("/api/admin/images/<path:name>")
@admin_required
def image(name):
    # photos of missing people are sensitive: only logged-in staff can view them
    folder, fname = resolve_photo_path(name)
    if os.path.isfile(os.path.join(folder, fname)):
        return send_from_directory(folder, fname)
    norm = (name or "").replace("\\", "/").lstrip("/")
    d = db()
    doc = (
        d.missing_persons.find_one({"photo": norm}, {"photo_bytes": 1})
        or d.sightings.find_one({"photo": norm}, {"photo_bytes": 1})
    )
    if doc and doc.get("photo_bytes"):
        return Response(bytes(doc["photo_bytes"]), mimetype="image/jpeg")
    return err("Image not found", 404)

@app.errorhandler(413)
def too_big(_):
    return err("Photo is too large (max 10 MB)", 413)

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through standard HTTP errors (like 404, 401, 403, 413)
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code

    traceback.print_exc()

    # Friendly, actionable messages for database errors
    if isinstance(e, PyMongoError) or "mongo" in type(e).__name__.lower():
        uri_val = os.environ.get("MONGO_URI", "").strip()
        if not uri_val:
            msg = (
                "Database error: MONGO_URI environment variable is not configured. "
                "Please add MONGO_URI in your Render Dashboard (Environment tab) "
                "with your MongoDB Atlas connection string."
            )
        elif "<password>" in uri_val or "<db_password>" in uri_val:
            msg = (
                "Database error: MONGO_URI still contains the '<password>' placeholder. "
                "Please replace it with your actual MongoDB Atlas password in Render Environment settings."
            )
        else:
            msg = (
                "Database connection error: Could not reach MongoDB. "
                "Please check your MONGO_URI and ensure MongoDB Atlas -> Network Access -> "
                "IP Access List has '0.0.0.0/0' (Allow access from anywhere) enabled."
            )
        return jsonify({"error": msg, "details": str(e)}), 503

    # For other unhandled exceptions: return JSON so UI shows actual problem instead of raw HTTP 500
    return jsonify({
        "error": f"Server error ({type(e).__name__}): {str(e)}"
    }), 500

if __name__ == "__main__":
    try:
        init_db()
    except PyMongoError as e:
        print("[error] Could not connect to MongoDB. Start MongoDB locally or set MONGO_URI:", e)
        raise SystemExit(1)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
