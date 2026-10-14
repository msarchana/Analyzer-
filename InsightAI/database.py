import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from config import DB_PATH

def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connection() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','admin')),
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            source_name TEXT NOT NULL DEFAULT 'manual',
            text_preview TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            topic TEXT NOT NULL,
            topic_score REAL NOT NULL,
            keywords TEXT NOT NULL DEFAULT '',
            word_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL DEFAULT 'system',
            event TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'INFO',
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user_created ON analyses(user_id, created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON audit_logs(created_at)")

def add_user(username, email, password_hash, role="user"):
    with connection() as c:
        cur = c.execute(
            "INSERT INTO users(username,email,password_hash,role,active,created_at) VALUES(?,?,?,?,1,?)",
            (username.strip(), email.strip().lower(), password_hash, role, now_iso()))
        return cur.lastrowid

def get_user_by_login(login):
    with connection() as c:
        return c.execute("SELECT * FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
                         (login.strip(), login.strip())).fetchone()

def get_user_by_id(user_id):
    with connection() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

def list_users():
    with connection() as c:
        return c.execute("SELECT id,username,email,role,active,created_at FROM users ORDER BY created_at DESC").fetchall()

def set_user_active(user_id, active):
    with connection() as c:
        c.execute("UPDATE users SET active=? WHERE id=? AND role!='admin'", (int(active), int(user_id)))

def set_user_role(user_id, role):
    with connection() as c:
        c.execute("UPDATE users SET role=? WHERE id=?", (role, int(user_id)))

def save_analysis(user_id, source_name, text, sentiment, sentiment_score, topic, topic_score, keywords):
    words = len(text.split())
    with connection() as c:
        cur = c.execute("""INSERT INTO analyses
        (user_id,source_name,text_preview,sentiment,sentiment_score,topic,topic_score,keywords,word_count,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (user_id, source_name[:120], text[:500], sentiment, float(sentiment_score), topic,
         float(topic_score), ", ".join(keywords), words, now_iso()))
        return cur.lastrowid

def get_analyses(user_id=None, limit=500):
    with connection() as c:
        if user_id is None:
            return c.execute("""SELECT a.*,u.username FROM analyses a JOIN users u ON u.id=a.user_id
                                ORDER BY a.created_at DESC LIMIT ?""", (int(limit),)).fetchall()
        return c.execute("SELECT * FROM analyses WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                         (int(user_id), int(limit))).fetchall()

def delete_analysis(analysis_id, user_id=None):
    with connection() as c:
        if user_id is None:
            c.execute("DELETE FROM analyses WHERE id=?", (int(analysis_id),))
        else:
            c.execute("DELETE FROM analyses WHERE id=? AND user_id=?", (int(analysis_id), int(user_id)))

def log_event(user_id, username, event, status="INFO", details=""):
    # Do not put passwords, access tokens, or full text in logs.
    safe_details = str(details).replace("\n", " ")[:500]
    with connection() as c:
        c.execute("INSERT INTO audit_logs(user_id,username,event,status,details,created_at) VALUES(?,?,?,?,?,?)",
                  (user_id, username or "system", event[:100], status[:20], safe_details, now_iso()))

def get_logs(limit=500):
    with connection() as c:
        return c.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (int(limit),)).fetchall()

def admin_stats():
    with connection() as c:
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = c.execute("SELECT COUNT(*) FROM users WHERE active=1").fetchone()[0]
        analyses = c.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        errors = c.execute("SELECT COUNT(*) FROM audit_logs WHERE status='ERROR'").fetchone()[0]
        return {"users": users, "active_users": active, "analyses": analyses, "errors": errors}
