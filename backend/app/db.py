import sqlite3
import numpy as np
import time
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    salt TEXT NOT NULL,
    pw_hash TEXT NOT NULL,
    threshold REAL NOT NULL DEFAULT 0.85,
    use_guard INTEGER NOT NULL DEFAULT 1,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ts REAL NOT NULL,
    question TEXT NOT NULL,
    hit INTEGER NOT NULL,
    reason TEXT NOT NULL,
    similarity REAL NOT NULL,
    latency_ms REAL NOT NULL,
    tokens INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id, id);
CREATE TABLE IF NOT EXISTS cache_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    faq_id INTEGER,
    created REAL NOT NULL,
    ttl_days REAL NOT NULL
    ,vector BLOB
);
CREATE INDEX IF NOT EXISTS idx_entries_user ON cache_entries(user_id);
"""


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)
        columns = {row["name"] for row in c.execute("PRAGMA table_info(cache_entries)")}
        if "vector" not in columns:
            c.execute("ALTER TABLE cache_entries ADD COLUMN vector BLOB")


# ---------- users ----------
def create_user(username, salt, pw_hash):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO users (username, salt, pw_hash, created) VALUES (?,?,?,?)",
            (username, salt, pw_hash, time.time()),
        )
        return cur.lastrowid


def get_user_by_name(username):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


def get_user(user_id):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def update_settings(user_id, threshold, use_guard):
    with conn() as c:
        c.execute(
            "UPDATE users SET threshold=?, use_guard=? WHERE id=?",
            (threshold, 1 if use_guard else 0, user_id),
        )


# ---------- logs ----------
def add_log(user_id, question, hit, reason, similarity, latency_ms, tokens):
    with conn() as c:
        c.execute(
            "INSERT INTO logs (user_id, ts, question, hit, reason, similarity, latency_ms, tokens)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (user_id, time.time(), question, 1 if hit else 0, reason, similarity, latency_ms, tokens),
        )


def get_logs(user_id, limit=None):
    sql = "SELECT * FROM logs WHERE user_id=? ORDER BY id DESC"
    args = [user_id]
    if limit:
        sql += " LIMIT ?"
        args.append(limit)
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def clear_logs(user_id):
    with conn() as c:
        c.execute("DELETE FROM logs WHERE user_id=?", (user_id,))


# ---------- cache entries (so the cache survives a server restart) ----------
def save_entry(user_id, question, answer, faq_id, created, ttl_days, vector=None):
    vector_blob = vector.astype("float32").tobytes() if vector is not None else None
    with conn() as c:
        c.execute(
            "INSERT INTO cache_entries (user_id, question, answer, faq_id, created, ttl_days, vector)"
            " VALUES (?,?,?,?,?,?,?)",
            (user_id, question, answer, faq_id, created, ttl_days, vector_blob),
        )


def load_entries(user_id):
    with conn() as c:
        rows = c.execute(
            "SELECT question, answer, faq_id, created, ttl_days, vector FROM cache_entries"
            " WHERE user_id=? ORDER BY id",
            (user_id,),
        ).fetchall()
        entries = []
        for row in rows:
            entry = dict(row)
            if entry["vector"] is not None:
                entry["vector"] = np.frombuffer(entry["vector"], dtype="float32").reshape(1, -1)
            entries.append(entry)
        return entries


def clear_entries(user_id):
    with conn() as c:
        c.execute("DELETE FROM cache_entries WHERE user_id=?", (user_id,))
