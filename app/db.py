"""Tiny database layer.

- Locally (no TURSO_DATABASE_URL set): a plain SQLite file, portfolio.db
- On Render: your Turso database via the official `libsql` client

All tables are prefixed with `pf_` so they can live in the same Turso
database as Tooltrick without colliding with its tables.
"""
import os
import sqlite3
import threading

TURSO_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
LOCAL_PATH = os.getenv("LOCAL_DB_PATH", "portfolio.db")

_lock = threading.Lock()


def _connect():
    if TURSO_URL:
        import libsql  # only needed in production

        return libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)
    return sqlite3.connect(LOCAL_PATH)


def _rows(cur):
    if cur.description is None:
        return []
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def query(sql, params=()):
    """Run a SELECT, return a list of dicts."""
    with _lock:
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            return _rows(cur)
        finally:
            conn.close()


def one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run a write statement, return lastrowid."""
    with _lock:
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS pf_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        name TEXT, headline TEXT, intro TEXT, about_md TEXT,
        callout TEXT, quote TEXT, location TEXT, email TEXT,
        linkedin TEXT, github TEXT, photo_id INTEGER, resume_id INTEGER,
        skills TEXT, certifications TEXT, pillars TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS pf_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        hook TEXT, objective TEXT, goals TEXT, applications TEXT,
        steps_json TEXT, mermaid TEXT, learned TEXT,
        video_url TEXT, github_url TEXT, tags TEXT,
        cover_id INTEGER,
        published INTEGER DEFAULT 0, featured INTEGER DEFAULT 0,
        position INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS pf_diagrams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        file_id INTEGER NOT NULL,
        caption TEXT, position INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS pf_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, content_type TEXT, data BLOB,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
]


# columns added after the first release; added automatically to existing tables
MIGRATIONS = ["ALTER TABLE pf_profile ADD COLUMN pillars TEXT"]


def init_db():
    for stmt in SCHEMA:
        execute(stmt)
    for stmt in MIGRATIONS:
        try:
            execute(stmt)
        except Exception:
            pass  # column already exists
    if not one("SELECT id FROM pf_profile WHERE id = 1"):
        execute(
            """INSERT INTO pf_profile (id, name, headline, intro, about_md, callout, quote,
                   location, skills, certifications, pillars)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Ronnie Nieuwenburg",
                "Aspiring Cloud Solutions Architect",
                "Hands-on AWS and Azure projects: the architecture, the build steps, and what I learned along the way.",
                "Write something about yourself here. Log in at **/admin** and open *Profile & resume* to edit this text.",
                "New projects are added as I build them. Each one shows the goals, the services used, diagrams and every step.",
                "I learn cloud by building real things, breaking them, and writing down how I fixed them.",
                "Netherlands",
                "AWS, Azure, Docker, Kubernetes, Terraform, Python, Linux, GitHub Actions",
                "AWS Certified SysOps Administrator – Associate\nMicrosoft Certified: Azure Administrator Associate",
                "Secure | by Design\nScalable | by Architecture\nReliable | by Experience\nFocused | on Outcomes",
            ),
        )
