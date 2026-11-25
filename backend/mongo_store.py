"""
MongoDB persistence layer for MPIS.
Uses MONGO_URI (default: mongodb://localhost:27017) and MONGO_DB (default: mpis).
Collections:
  - users
  - missing_persons
  - sightings
  - matches
  - notifications
  - history
  - counters
"""
import os
import datetime
import sqlite3
import numpy as np
from pymongo import MongoClient, ReturnDocument, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.environ.get("MONGO_DB", "mpis")

_client = None
_db = None


def get_mongo_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        _db = _client[MONGO_DB_NAME]
    return _db


def next_id(mdb, name: str) -> int:
    doc = mdb.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])


def clean_doc(doc):
    if not doc:
        return None
    out = dict(doc)
    out.pop("_id", None)
    out.pop("embedding", None)
    return out


def format_code(kind: str, seq_id: int, created_at: str | None = None) -> str:
    prefix = "MP" if kind == "missing_person" else "SG"
    year = (created_at or "")[:4]
    if not year.isdigit():
        year = str(datetime.datetime.now().year)
    return f"{prefix}-{year}-{int(seq_id):04d}"


def backfill_codes(mdb):
    for doc in mdb.missing_persons.find({"code": {"$exists": False}}, {"_id": 1, "id": 1, "created_at": 1}):
        mdb.missing_persons.update_one(
            {"_id": doc["_id"]},
            {"$set": {"code": format_code("missing_person", doc["id"], doc.get("created_at"))}},
        )
    for doc in mdb.sightings.find({"code": {"$exists": False}}, {"_id": 1, "id": 1, "created_at": 1}):
        mdb.sightings.update_one(
            {"_id": doc["_id"]},
            {"$set": {"code": format_code("sighting", doc["id"], doc.get("created_at"))}},
        )


def ensure_indexes(mdb):
    mdb.users.create_index([("username", ASCENDING)], unique=True)
    mdb.missing_persons.create_index([("id", ASCENDING)], unique=True)
    mdb.missing_persons.create_index([("code", ASCENDING)], unique=True, sparse=True)
    mdb.missing_persons.create_index([("status", ASCENDING)])
    mdb.sightings.create_index([("id", ASCENDING)], unique=True)
    mdb.sightings.create_index([("code", ASCENDING)], unique=True, sparse=True)
    mdb.matches.create_index([("id", ASCENDING)], unique=True)
    mdb.matches.create_index([("case_id", ASCENDING), ("sighting_id", ASCENDING)], unique=True)
    mdb.matches.create_index([("status", ASCENDING), ("score", DESCENDING)])
    mdb.notifications.create_index([("id", ASCENDING)], unique=True)
    mdb.notifications.create_index([("match_id", ASCENDING)])
    mdb.history.create_index([("case_id", ASCENDING), ("id", ASCENDING)])


def migrate_from_sqlite(mdb, sqlite_path: str):
    """One-time migration from legacy SQLite mpis.db if MongoDB collections are still empty."""
    if not os.path.isfile(sqlite_path):
        return
    if mdb.missing_persons.count_documents({}) > 0 or mdb.sightings.count_documents({}) > 0:
        return

    con = sqlite3.connect(sqlite_path)
    con.row_factory = sqlite3.Row
    try:
        for u in con.execute("SELECT * FROM users").fetchall():
            mdb.users.update_one(
                {"username": u["username"]},
                {"$setOnInsert": {
                    "id": int(u["id"]),
                    "username": u["username"],
                    "password_hash": u["password_hash"],
                    "role": u["role"],
                }},
                upsert=True,
            )

        for r in con.execute("SELECT * FROM cases").fetchall():
            doc = dict(r)
            doc["embedding"] = np.frombuffer(r["embedding"], dtype="float32").tolist()
            mdb.missing_persons.insert_one(doc)

        for r in con.execute("SELECT * FROM sightings").fetchall():
            doc = dict(r)
            doc["embedding"] = np.frombuffer(r["embedding"], dtype="float32").tolist()
            mdb.sightings.insert_one(doc)

        for r in con.execute("SELECT * FROM matches").fetchall():
            mdb.matches.insert_one(dict(r))

        for r in con.execute("SELECT * FROM notifications").fetchall():
            mdb.notifications.insert_one(dict(r))

        for r in con.execute("SELECT * FROM history").fetchall():
            mdb.history.insert_one(dict(r))

        for counter_name, tbl in [
            ("users", "users"),
            ("missing_persons", "cases"),
            ("sightings", "sightings"),
            ("matches", "matches"),
            ("notifications", "notifications"),
            ("history", "history"),
        ]:
            max_id = con.execute(f"SELECT COALESCE(MAX(id), 0) FROM {tbl}").fetchone()[0]
            if max_id:
                mdb.counters.update_one(
                    {"_id": counter_name},
                    {"$max": {"seq": int(max_id)}},
                    upsert=True,
                )
        print(f"[mongo] migrated existing records from {sqlite_path} into MongoDB '{mdb.name}'")
    finally:
        con.close()


def init_mongo(sqlite_path: str | None = None):
    mdb = get_mongo_db()
    ensure_indexes(mdb)
    if sqlite_path:
        migrate_from_sqlite(mdb, sqlite_path)
    backfill_codes(mdb)
    if mdb.users.count_documents({}) == 0:
        pw = os.environ.get("ADMIN_PASSWORD", "admin123")
        mdb.users.insert_one({
            "id": next_id(mdb, "users"),
            "username": "admin",
            "password_hash": generate_password_hash(pw),
            "role": "admin",
        })
        print("[setup] Created admin user 'admin' in MongoDB. Set ADMIN_PASSWORD env var before deployment.")
    return mdb
