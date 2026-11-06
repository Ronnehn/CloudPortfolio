# ==============================================================================
# DATA LAYER
# ------------------------------------------------------------------------------
# Database/auth helpers, CSV import/export utilities, and SVG/BBCode generators.
# ==============================================================================
import io
import sqlite3
import warnings
import hashlib
import os
import base64
import json
import secrets
import pandas as pd
import numpy as np
from functools import lru_cache

from ht_engine import *
from richtskills_data import RICHTSKILLS_AGE_MIN, RICHTSKILLS_AGE_MAX, RICHTSKILLS_DEFAULT, RICHTSKILLS_U21_DEFAULT

# ------------------------------------------------------------------------------
# Custom Cache Decorator
# ------------------------------------------------------------------------------
def cache_data(ttl=None):
    def decorator(func):
        cached_func = lru_cache(maxsize=None)(func)
        cached_func.clear = cached_func.cache_clear
        return cached_func
    if callable(ttl):
        func = ttl
        cached_func = lru_cache(maxsize=None)(func)
        cached_func.clear = cached_func.cache_clear
        return cached_func
    return decorator

# ==============================================================================
# 1. DATABASE CONNECTION & AUTH
# ==============================================================================
DB_STATUS = {'backend': 'unknown', 'detail': ''}
TURSO_FAILED = False

def get_db_connection():
    global TURSO_FAILED
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')

    if turso_url and turso_token and not TURSO_FAILED:
        try:
            import libsql
            conn = libsql.connect(database=turso_url, auth_token=turso_token)
            DB_STATUS['backend'] = 'turso'
            DB_STATUS['detail'] = turso_url
            return conn
        except Exception as e:
            TURSO_FAILED = True
            DB_STATUS['backend'] = 'sqlite (turso failed)'
            DB_STATUS['detail'] = f'{type(e).__name__}: {e}'
            return sqlite3.connect('skills_app_2.db')

    if TURSO_FAILED:
        DB_STATUS['backend'] = 'sqlite (turso failed)'
    else:
        DB_STATUS['backend'] = 'sqlite (no turso credentials found)'
        
    return sqlite3.connect('skills_app_2.db')

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', str(password or "").strip().encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + pwd_hash).decode('utf-8')

def verify_user(username, password):
    if not username or not password: return False
    try:
        conn = get_db_connection()
        row = conn.cursor().execute('SELECT password FROM users WHERE LOWER(username) = LOWER(?);', (str(username).strip(),)).fetchone()
        conn.close()
        if row and row[0]:
            stored_pass, entered_pass = row[0], str(password).strip()
            if stored_pass == entered_pass: return True
            stored_bytes = base64.b64decode(stored_pass.encode('utf-8'))
            return hashlib.pbkdf2_hmac('sha256', entered_pass.encode('utf-8'), stored_bytes[:16], 100000) == stored_bytes[16:]
    except: pass
    return False

@cache_data
def init_user_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL);')
    user_cols = [col[1] for col in cursor.execute("PRAGMA table_info(users);").fetchall()]
    if 'last_login' not in user_cols: cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT;")
    if 'last_seen' not in user_cols: cursor.execute("ALTER TABLE users ADD COLUMN last_seen TEXT;")
    cursor.execute('CREATE TABLE IF NOT EXISTS login_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, login_time TEXT NOT NULL);')
    cursor.execute('CREATE TABLE IF NOT EXISTS skills_data (username TEXT, PlayerID INTEGER, Speler TEXT, Positie TEXT, Leeftijd INTEGER, "dag(en)" INTEGER, Specialiteit TEXT, Vorm REAL, Conditie REAL, Ervaring REAL, TSI REAL, Loon REAL, HTMS REAL, HTMS28 REAL, GK REAL, DE REAL, PM REAL, WI REAL, Pas REAL, SC REAL, SH REAL);')
    cursor.execute('CREATE TABLE IF NOT EXISTS country_richtskills (country TEXT PRIMARY KEY, skills_json TEXT, u21_skills_json TEXT);')
    cursor.execute('CREATE TABLE IF NOT EXISTS country_age_richtskills (country TEXT NOT NULL, age INTEGER NOT NULL, skills_json TEXT, PRIMARY KEY (country, age));')
    cursor.execute('CREATE TABLE IF NOT EXISTS reference_players (id INTEGER PRIMARY KEY AUTOINCREMENT, PlayerID INTEGER, Speler TEXT, Nationality TEXT, Positie TEXT, Specialiteit TEXT, Leeftijd INTEGER, "dag(en)" INTEGER, TSI REAL, Loon REAL, HTMS REAL, HTMS28 REAL, GK REAL, DE REAL, PM REAL, WI REAL, Pas REAL, SC REAL, SH REAL, source TEXT, added_by TEXT, added_date TEXT);')
    _ref_cols = [col[1] for col in cursor.execute("PRAGMA table_info(reference_players);").fetchall()]
    if 'Foreign' not in _ref_cols:   # plays abroad: the wage includes Hattrick's +20% bonus
        cursor.execute('ALTER TABLE reference_players ADD COLUMN "Foreign" INTEGER DEFAULT 0;')
    # Old skill values of Reference DB rows before a bulk re-estimate, so it can be undone.
    cursor.execute('CREATE TABLE IF NOT EXISTS reference_backup (id INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT NOT NULL, ref_id INTEGER NOT NULL, data_json TEXT, saved_at TEXT);')
    cursor.execute('CREATE TABLE IF NOT EXISTS session_tokens (token TEXT PRIMARY KEY, username TEXT NOT NULL, created_at TEXT, expires_at TEXT);')
    cursor.execute('CREATE TABLE IF NOT EXISTS watchlists (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, list_name TEXT NOT NULL, player_name TEXT NOT NULL, UNIQUE(username, list_name, player_name));')
    # Named lineups (players, roles, match settings and the calculated ratings) for the Score Predictor.
    cursor.execute('CREATE TABLE IF NOT EXISTS saved_lineups (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, name TEXT NOT NULL, saved_at TEXT, data_json TEXT, UNIQUE(username, name));')
    cursor.execute('CREATE TABLE IF NOT EXISTS saved_predictions (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, name TEXT NOT NULL, saved_at TEXT, data_json TEXT, UNIQUE(username, name));')

    cols = [col[1] for col in cursor.execute("PRAGMA table_info(skills_data);").fetchall()]
    if 'username' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN username TEXT;"); cursor.execute("UPDATE skills_data SET username = 'admin' WHERE username IS NULL OR username = '';")
    if 'PlayerID' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN PlayerID INTEGER;")
    if 'HTMS' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN HTMS REAL;")
    if 'HTMS28' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN HTMS28 REAL;")
    if 'Vorm' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN Vorm REAL;")
    if 'Conditie' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN Conditie REAL;")
    if 'Nationality' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN Nationality TEXT;")
    if 'Injuries' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN Injuries REAL;")
    if 'Transfer-listed' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN "Transfer-listed" TEXT;')
    if 'Leiderschap' not in cols: cursor.execute("ALTER TABLE skills_data ADD COLUMN Leiderschap REAL;")
    if 'Matches for the national team' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN "Matches for the national team" INTEGER;')
    if 'Matches for the national U21 team' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN "Matches for the national U21 team" INTEGER;')
    if 'National team player' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN "National team player" INTEGER;')
    # Plays abroad: wage is 20% higher — needed to read skills from the wage correctly.
    if 'Foreign' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN "Foreign" INTEGER DEFAULT 0;')
    # 1 = the stored HTMS/HTMS28 is an estimate (solver or import), not the player's real HTMS.
    if 'HTMS_est' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN HTMS_est INTEGER DEFAULT 0;')
    # Performance history: TSI at 22 (NT baseline) and at 17 (U22 baseline), kept on every reimport.
    if 'TSI_22' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN TSI_22 REAL;')
    if 'TSI_17' not in cols: cursor.execute('ALTER TABLE skills_data ADD COLUMN TSI_17 REAL;')
    # Earlier imports of a player: moved here when a newer import replaces his row.
    cursor.execute('CREATE TABLE IF NOT EXISTS player_history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, '
                   'PlayerID INTEGER, Speler TEXT, Positie TEXT, Leeftijd INTEGER, "dag(en)" INTEGER, TSI REAL, Loon REAL, '
                   'Vorm REAL, Conditie REAL, GK REAL, DE REAL, PM REAL, WI REAL, Pas REAL, SC REAL, SH REAL, saved_at TEXT);')

    for username, plain_password in {'admin': 'hattrick123'}.items():
        if not cursor.execute('SELECT password FROM users WHERE LOWER(username) = LOWER(?);', (username,)).fetchone():
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?);', (username, hash_password(plain_password)))
            if cursor.execute('SELECT COUNT(*) FROM skills_data WHERE LOWER(username) = LOWER(?);', (username,)).fetchone()[0] == 0:
                ex = DEFAULT_EXAMPLE_PLAYER.copy(); ex['username'] = username
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', category=UserWarning)
                    pd.DataFrame([ex]).to_sql('skills_data', conn, if_exists='append', index=False)
    # Repair: form above 8 / stamina above 9.4 (Hattrick's maxima; stamina per Schum) from an old 'Find Form & Stamina'
    # fallback that used level + 0.5 (e.g. stamina 9.5).
    try:
        cursor.execute('UPDATE skills_data SET Vorm=8.0 WHERE Vorm > 8.0;')
        cursor.execute('UPDATE skills_data SET Conditie=9.4 WHERE Conditie > 9.4;')
    except Exception as _e:
        print(f'form/stamina repair skipped: {_e}')
    # Repair: lineup roles stored as roster positions by the old "Save lineup" button
    # (CD, W, IM, FW, ...). The solver needs position codes; 'CD' made centre-backs solve as forwards.
    try:
        for _alias, _code in POSITION_ALIASES.items():
            if _alias != _code:
                cursor.execute('UPDATE skills_data SET Positie=? WHERE Positie=?;', (_code, _alias))
    except Exception as _e:
        print(f'position repair skipped: {_e}')
    conn.commit(); conn.close()

def register_user(username, password):
    u = username.strip()
    try:
        conn = get_db_connection()
        if conn.cursor().execute('SELECT username FROM users WHERE LOWER(username) = LOWER(?);', (u,)).fetchone(): return False
        conn.cursor().execute('INSERT INTO users (username, password) VALUES (?, ?);', (u, hash_password(password)))
        if conn.cursor().execute('SELECT COUNT(*) FROM skills_data WHERE LOWER(username) = LOWER(?);', (u,)).fetchone()[0] == 0:
            ex = DEFAULT_EXAMPLE_PLAYER.copy(); ex['username'] = u
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', category=UserWarning)
                pd.DataFrame([ex]).to_sql('skills_data', conn, if_exists='append', index=False)
        conn.commit(); conn.close()
        get_all_usernames.clear()
        return True
    except: return False

def update_user_password(username, old_password, new_password):
    if not verify_user(username, old_password): return False, "Incorrect current password!"
    try:
        conn = get_db_connection()
        conn.cursor().execute('UPDATE users SET password = ? WHERE LOWER(username) = LOWER(?);', (hash_password(new_password), username.strip()))
        conn.commit(); conn.close()
        return True, "Password updated successfully!"
    except Exception as e: return False, f"Database error: {e}"

def delete_user(username):
    try:
        conn = get_db_connection()
        conn.cursor().execute('DELETE FROM users WHERE LOWER(username) = LOWER(?);', (username.strip(),))
        conn.cursor().execute('DELETE FROM skills_data WHERE LOWER(username) = LOWER(?);', (username.strip(),))
        conn.commit(); conn.close()
        get_all_usernames.clear()
        return True, f"User '{username}' and their roster data have been deleted successfully!"
    except Exception as e: return False, f"Database error: {e}"

@cache_data
def get_all_usernames():
    conn = get_db_connection()
    users = [row[0] for row in conn.cursor().execute('SELECT username FROM users;').fetchall()]
    conn.close()
    return users

ONLINE_THRESHOLD_SECONDS = 90
def record_login(username):
    try:
        now_iso = pd.Timestamp.now('UTC').isoformat()
        conn = get_db_connection()
        conn.cursor().execute('UPDATE users SET last_login = ?, last_seen = ? WHERE LOWER(username) = LOWER(?);', (now_iso, now_iso, username.strip()))
        conn.cursor().execute('INSERT INTO login_log (username, login_time) VALUES (?, ?);', (username.strip(), now_iso))
        conn.commit(); conn.close()
    except: pass

def get_logins_since(since_iso, exclude_username=None):
    try:
        conn = get_db_connection()
        if exclude_username: rows = conn.cursor().execute('SELECT username, login_time FROM login_log WHERE login_time > ? AND LOWER(username) != LOWER(?) ORDER BY login_time ASC;', (since_iso, exclude_username.strip())).fetchall()
        else: rows = conn.cursor().execute('SELECT username, login_time FROM login_log WHERE login_time > ? ORDER BY login_time ASC;', (since_iso,)).fetchall()
        conn.close()
        return rows
    except: return []

def record_heartbeat(username):
    try:
        now_iso = pd.Timestamp.now('UTC').isoformat()
        conn = get_db_connection()
        conn.cursor().execute('UPDATE users SET last_seen = ? WHERE LOWER(username) = LOWER(?);', (now_iso, username.strip()))
        conn.commit(); conn.close()
    except: pass

def get_users_with_status():
    conn = get_db_connection()
    rows = conn.cursor().execute('SELECT username, last_login, last_seen FROM users;').fetchall()
    conn.close()
    now, result = pd.Timestamp.now('UTC'), []
    for username, last_login, last_seen in rows:
        online = False
        if last_seen:
            try:
                seen_ts = pd.Timestamp(last_seen)
                if seen_ts.tzinfo is None: seen_ts = seen_ts.tz_localize('UTC')
                online = (now - seen_ts).total_seconds() <= ONLINE_THRESHOLD_SECONDS
            except: pass
        result.append({'username': username, 'last_login': last_login, 'last_seen': last_seen, 'online': online})
    return result

SESSION_TOKEN_TTL_DAYS = 30

def create_session_token(username):
    token = secrets.token_urlsafe(32)
    now = pd.Timestamp.now('UTC')
    expires = now + pd.Timedelta(days=SESSION_TOKEN_TTL_DAYS)
    try:
        conn = get_db_connection()
        conn.cursor().execute('INSERT INTO session_tokens (token, username, created_at, expires_at) VALUES (?, ?, ?, ?);',
                               (token, username.strip(), now.isoformat(), expires.isoformat()))
        conn.commit(); conn.close()
        return token
    except: return None

def validate_session_token(token):
    if not token: return None
    try:
        conn = get_db_connection()
        row = conn.cursor().execute('SELECT username, expires_at FROM session_tokens WHERE token = ?;', (token,)).fetchone()
        conn.close()
        if not row: return None
        username, expires_at = row
        if pd.Timestamp(expires_at) < pd.Timestamp.now('UTC'): 
            delete_session_token(token)
            return None
        return username
    except: return None

def delete_session_token(token):
    if not token: return
    try:
        conn = get_db_connection()
        conn.cursor().execute('DELETE FROM session_tokens WHERE token = ?;', (token,))
        conn.commit(); conn.close()
    except: pass

@cache_data
def get_country_richtskills(country):
    if not country or not str(country).strip():
        return RICHTSKILLS_DEFAULT, RICHTSKILLS_U21_DEFAULT
    c = str(country).strip()
    conn = get_db_connection()
    row = conn.cursor().execute('SELECT skills_json, u21_skills_json FROM country_richtskills WHERE country = ?;', (c,)).fetchone()
    conn.close()

    sen_skills, u21_skills = RICHTSKILLS_DEFAULT.copy(), RICHTSKILLS_U21_DEFAULT.copy()
    if row:
        if row[0]:
            try: sen_skills.update(json.loads(row[0]))
            except: pass
        if row[1]:
            try: u21_skills.update(json.loads(row[1]))
            except: pass
    for pos, bench in RICHTSKILLS_DEFAULT.items():
        if pos not in sen_skills: sen_skills[pos] = bench
    for pos, bench in RICHTSKILLS_U21_DEFAULT.items():
        if pos not in u21_skills: u21_skills[pos] = bench
    return sen_skills, u21_skills

def save_country_richtskills(country, skills_dict, is_u21=False):
    c = str(country).strip()
    if not c: return False
    skills_json = json.dumps(skills_dict)
    conn = get_db_connection()
    cursor = conn.cursor()
    exists = cursor.execute('SELECT country FROM country_richtskills WHERE country = ?;', (c,)).fetchone()
    if not exists:
        if is_u21: cursor.execute('INSERT INTO country_richtskills (country, skills_json, u21_skills_json) VALUES (?, ?, ?);', (c, json.dumps(RICHTSKILLS_DEFAULT), skills_json))
        else: cursor.execute('INSERT INTO country_richtskills (country, skills_json, u21_skills_json) VALUES (?, ?, ?);', (c, skills_json, json.dumps(RICHTSKILLS_U21_DEFAULT)))
    else:
        if is_u21: cursor.execute('UPDATE country_richtskills SET u21_skills_json = ? WHERE country = ?;', (skills_json, c))
        else: cursor.execute('UPDATE country_richtskills SET skills_json = ? WHERE country = ?;', (skills_json, c))
    conn.commit()
    conn.close()
    get_country_richtskills.clear()
    return True

@cache_data
def get_country_age_richtskills(country, age):
    c = str(country).strip()
    if not c: return None
    conn = get_db_connection()
    row = conn.cursor().execute('SELECT skills_json FROM country_age_richtskills WHERE country = ? AND age = ?;', (c, int(age))).fetchone()
    conn.close()
    if row and row[0]:
        try: return json.loads(row[0])
        except: return None
    return None

def save_country_age_richtskills(country, age, skills_dict):
    c = str(country).strip()
    if not c: return False
    skills_json = json.dumps(skills_dict)
    conn = get_db_connection()
    cursor = conn.cursor()
    exists = cursor.execute('SELECT 1 FROM country_age_richtskills WHERE country = ? AND age = ?;', (c, int(age))).fetchone()
    if exists: cursor.execute('UPDATE country_age_richtskills SET skills_json = ? WHERE country = ? AND age = ?;', (skills_json, c, int(age)))
    else: cursor.execute('INSERT INTO country_age_richtskills (country, age, skills_json) VALUES (?, ?, ?);', (c, int(age), skills_json))
    conn.commit()
    conn.close()
    get_country_age_richtskills.clear()
    return True

def delete_country_age_richtskills(country, age):
    c = str(country).strip()
    if not c: return False
    conn = get_db_connection()
    conn.cursor().execute('DELETE FROM country_age_richtskills WHERE country = ? AND age = ?;', (c, int(age)))
    conn.commit()
    conn.close()
    get_country_age_richtskills.clear()
    return True

def get_richtskills_for_age(country, age, spec=None):
    estimate = estimate_age_richtskills(age, spec, country)
    saved = get_country_age_richtskills(country, age)
    if saved:
        merged = estimate.copy()
        merged.update(saved)
        return merged
    return estimate

# ------------------------------------------------------------------------------
# Richtskills CSV/Excel export & import
# ------------------------------------------------------------------------------
RICHTSKILLS_SKILL_COLS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']
RICHTSKILLS_EXPORT_COLUMNS = ['Age', 'Position', 'Custom'] + RICHTSKILLS_SKILL_COLS

def build_richtskills_dataframe(country):
    rows = []
    for age in range(RICHTSKILLS_AGE_MIN, RICHTSKILLS_AGE_MAX + 1):
        bench_all = get_richtskills_for_age(country, age)
        stored = get_country_age_richtskills(country, age) or {}
        for pos in RICHTSKILLS_DEFAULT.keys():
            b = bench_all.get(pos, {})
            row = {'Age': age, 'Position': pos, 'Custom': '✅' if pos in stored else ''}
            row.update({sk: round(float(b.get(sk, 1.0)), 2) for sk in RICHTSKILLS_SKILL_COLS})
            rows.append(row)
    return pd.DataFrame(rows, columns=RICHTSKILLS_EXPORT_COLUMNS)

def export_richtskills_to_csv(country):
    return build_richtskills_dataframe(country).to_csv(index=False).encode('utf-8')

def export_richtskills_to_excel(country):
    buffer = io.BytesIO()
    df = build_richtskills_dataframe(country)
    sheet_name = (str(country).strip()[:31] or 'Richtskills')
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    buffer.seek(0)
    return buffer

def read_richtskills_upload(uploaded_file):
    fname = str(getattr(uploaded_file, 'name', '')).lower()
    uploaded_file.seek(0)
    if fname.endswith('.xlsx') or fname.endswith('.xls'):
        return pd.read_excel(uploaded_file)
    return read_uploaded_csv(uploaded_file)

def import_richtskills_dataframe(df, country):
    if df is None or df.empty:
        return 0, 0

    work = df.copy()
    work['__Age__'] = clean_num_series(find_col_alias(work, ['Age', 'Leeftijd'])).fillna(-1)
    work['__Pos__'] = find_col_alias(work, ['Position', 'Positie', 'Pos']).astype(str).str.strip()
    work = work[work['__Pos__'].isin(RICHTSKILLS_DEFAULT.keys())]
    work['__Age__'] = work['__Age__'].astype(int)
    work = work[(work['__Age__'] >= RICHTSKILLS_AGE_MIN) & (work['__Age__'] <= RICHTSKILLS_AGE_MAX)]
    if work.empty:
        return 0, 0

    skill_aliases = {'GK': ['GK'], 'DE': ['DE', 'DEF'], 'PM': ['PM'], 'WI': ['WI', 'Wing'],
                      'Pas': ['Pas', 'PASS'], 'SC': ['SC', 'SCO'], 'SH': ['SH']}
    skill_series = {sk: clean_num_series(find_col_alias(work, aliases)) for sk, aliases in skill_aliases.items()}

    rows_applied, ages_touched = 0, set()
    for age in sorted(work['__Age__'].unique()):
        age_idx = work.index[work['__Age__'] == age]
        fallback_bench = get_richtskills_for_age(country, int(age))
        stored = get_country_age_richtskills(country, int(age)) or {}
        for idx in age_idx:
            pos = work.at[idx, '__Pos__']
            fallback = fallback_bench.get(pos, {})
            skills = {}
            for sk in RICHTSKILLS_SKILL_COLS:
                val = skill_series[sk].get(idx)
                skills[sk] = round(float(val), 2) if pd.notna(val) else round(float(fallback.get(sk, 1.0)), 2)
            stored[pos] = skills
            rows_applied += 1
        save_country_age_richtskills(country, int(age), stored)
        ages_touched.add(int(age))
    return rows_applied, len(ages_touched)

@cache_data
def load_user_db(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM skills_data WHERE LOWER(username) = LOWER(?)', (username,))
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]
    df = pd.DataFrame(rows, columns=col_names)
    conn.close()

    if 'username' in df.columns:
        df = df.drop(columns=['username'])
    return df


HISTORY_COLS = ['PlayerID', 'Speler', 'Positie', 'Leeftijd', 'dag(en)', 'TSI', 'Loon', 'Vorm', 'Conditie',
                'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']


def archive_player_rows(cursor, username, player_id, name, new_age=None, new_days=None):
    """Before a reimport replaces a player: copy his current row(s) to player_history (unless it is the same
    moment, i.e. same age and days). Returns his kept baselines {'TSI_22': .., 'TSI_17': ..}."""
    if player_id:
        where, args = 'LOWER(username)=LOWER(?) AND (PlayerID=? OR ((PlayerID IS NULL OR PlayerID=0) AND Speler=?))', \
                      (username, int(player_id), str(name))
    else:
        where, args = 'LOWER(username)=LOWER(?) AND Speler=?', (username, str(name))
    cols = ', '.join(f'"{c}"' for c in HISTORY_COLS)
    try:
        rows = cursor.execute(f'SELECT {cols}, TSI_22, TSI_17 FROM skills_data WHERE {where};', args).fetchall()
    except Exception:
        return {}
    keep = {}
    now = pd.Timestamp.now('UTC').isoformat()
    for r in rows:
        vals = dict(zip(HISTORY_COLS + ['TSI_22', 'TSI_17'], r))
        for k in ('TSI_22', 'TSI_17'):
            if vals.get(k) and not keep.get(k):
                keep[k] = vals[k]
        same = (new_age is not None and vals.get('Leeftijd') is not None and int(vals['Leeftijd'] or 0) == int(new_age)
                and int(vals.get('dag(en)') or 0) == int(new_days or 0))
        if same or not vals.get('TSI'):
            continue
        cursor.execute(f'INSERT INTO player_history (username, {cols}, saved_at) VALUES (?, {", ".join("?" * len(HISTORY_COLS))}, ?);',
                       (username, *[vals[c] for c in HISTORY_COLS], now))
    return keep


def get_player_history(username, player_id=None, name=None):
    """Earlier imports of one player, oldest first."""
    conn = get_db_connection()
    try:
        if player_id:
            rows = conn.cursor().execute('SELECT * FROM player_history WHERE LOWER(username)=LOWER(?) AND (PlayerID=? OR Speler=?) '
                                         'ORDER BY Leeftijd, "dag(en)";', (username, int(player_id), str(name or ''))).fetchall()
        else:
            rows = conn.cursor().execute('SELECT * FROM player_history WHERE LOWER(username)=LOWER(?) AND Speler=? '
                                         'ORDER BY Leeftijd, "dag(en)";', (username, str(name or ''))).fetchall()
        cols = [d[0] for d in conn.cursor().execute('SELECT * FROM player_history LIMIT 0;').description]
    except Exception:
        rows, cols = [], []
    conn.close()
    return pd.DataFrame(rows, columns=cols) if cols else pd.DataFrame()


def set_player_baseline(username, name, column, value):
    """Save a performance-history baseline (TSI_22 or TSI_17) for one player."""
    if column not in ('TSI_22', 'TSI_17'):
        return
    conn = get_db_connection()
    conn.cursor().execute(f'UPDATE skills_data SET {column}=? WHERE LOWER(username)=LOWER(?) AND Speler=?;',
                          (None if value in (None, '') else float(value), username, str(name)))
    conn.commit(); conn.close()
    load_user_db.clear()


def delete_player(username, player_name):
    """Permanently removes a single player from the user's roster."""
    try:
        conn = get_db_connection()
        conn.cursor().execute(
            'DELETE FROM skills_data WHERE LOWER(username) = LOWER(?) AND Speler = ?;',
            (username, player_name)
        )
        conn.commit()
        conn.close()
        load_user_db.clear()
        return True, f'✅ {player_name} removed from your roster.'
    except Exception as e:
        return False, f'Error deleting player: {e}'

# ==============================================================================
# 2. CSV HELPERS & SVG ENGINE
# ==============================================================================
def export_roster_to_excel(df_db):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_db.to_excel(writer, index=False, sheet_name='Roster')
    buffer.seek(0)
    return buffer

def build_pitch_overview_svg(pitch_layout, lineup_players, slot_pos_label, sector_ratings):
    W, H = 600, 900
    margin = 90
    row_y = [130, 340, 560, 780]
    row_sector_slots = [
        {'left': 'LA', 'center': 'CA', 'right': 'RA'},
        {'center': 'MID'},
        {'left': 'LD', 'center': 'CD', 'right': 'RD'},
        {},
    ]

    def _x_positions(n):
        if n <= 1: return [W / 2.0]
        step = (W - 2 * margin) / (n - 1)
        return [margin + i * step for i in range(n)]

    def _short_name(name):
        name = str(name or '?').strip()
        parts = name.replace("'", '').split()
        return parts[-1][:12] if parts else name[:12]

    svg_parts = [
        f'<div style="background:#0e1117;padding:10px;border-radius:12px;">',
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:820px;display:block;margin:0 auto;font-family:Arial,Helvetica,sans-serif;">',
        f'<rect x="20" y="20" width="{W-40}" height="{H-40}" rx="14" fill="#1C1C24" stroke="#3B3B4D" stroke-width="3"/>',
        f'<line x1="20" y1="{H/2}" x2="{W-20}" y2="{H/2}" stroke="#3B3B4D" stroke-width="2"/>',
        f'<circle cx="{W/2}" cy="{H/2}" r="70" fill="none" stroke="#3B3B4D" stroke-width="2"/>',
        f'<rect x="{W/2-90}" y="20" width="180" height="55" fill="none" stroke="#3B3B4D" stroke-width="2"/>',
        f'<rect x="{W/2-90}" y="{H-75}" width="180" height="55" fill="none" stroke="#3B3B4D" stroke-width="2"/>',
    ]

    def _badge(x, y, label, value):
        return (
            f'<g>'
            f'<rect x="{x-32}" y="{y-16}" width="64" height="32" rx="8" fill="#0e1117" stroke="#5B7A99" stroke-width="1.5" opacity="0.95"/>'
            f'<text x="{x}" y="{y-2}" text-anchor="middle" font-size="11" fill="#A9C1D9" font-weight="700">{label}</text>'
            f'<text x="{x}" y="{y+13}" text-anchor="middle" font-size="12" fill="#FAFAFA" font-weight="700">{value:.1f}</text>'
            f'</g>'
        )

    for row_idx, row_slots in enumerate(pitch_layout):
        n = len(row_slots)
        xs = _x_positions(n)
        y = row_y[row_idx] if row_idx < len(row_y) else row_y[-1]

        sector_map = row_sector_slots[row_idx] if row_idx < len(row_sector_slots) else {}
        if 'left' in sector_map: svg_parts.append(_badge(xs[0], y - 55, sector_map['left'], sector_ratings.get(sector_map['left'], 0.0)))
        if 'center' in sector_map:
            cx = xs[n // 2]
            svg_parts.append(_badge(cx, y - 55, sector_map['center'], sector_ratings.get(sector_map['center'], 0.0)))
        if 'right' in sector_map: svg_parts.append(_badge(xs[-1], y - 55, sector_map['right'], sector_ratings.get(sector_map['right'], 0.0)))

        for i, (slot_id, pos_label, allowed_roles) in enumerate(row_slots):
            x = xs[i]
            prow = lineup_players.get(slot_id)
            if prow:
                name = _short_name(prow.get('Speler'))
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="28" fill="#5B7A99" stroke="#0e1117" stroke-width="2.5"/>')
                svg_parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="12" fill="#FAFAFA" font-weight="700">{prow.get("Positie", "UNK")}</text>')
                svg_parts.append(f'<text x="{x}" y="{y+48}" text-anchor="middle" font-size="13" fill="#FAFAFA" font-weight="700">{name}</text>')
            else:
                svg_parts.append(f'<circle cx="{x}" cy="{y}" r="28" fill="none" stroke="#3B3B4D" stroke-width="2" stroke-dasharray="4,4"/>')
                svg_parts.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-size="10" fill="#7A7A87">empty</text>')

    svg_parts.append('</svg></div>')
    return ''.join(svg_parts)

def generate_score_predictor_htbbcode(scenario_results, nl, other, tactic_labels):
    rows_bbcode = ''
    for i, (res, (nl_tac_label, other_tac_label)) in enumerate(zip(scenario_results, tactic_labels)):
        delta = res['goals_nl'] - res['goals_o']
        delta_str = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
        rows_bbcode += (
            f"[tr][td]{i+1}[/td][td]{nl_tac_label}[/td][td]{other_tac_label}[/td]"
            f"[td]{res['goals_nl']:.2f}[/td][td]{res['goals_o']:.2f}[/td][td][b]{delta_str}[/b][/td][/tr]"
        )
    header_block = (
        f"[b]Your Team:[/b] MID {nl['MID']:.1f} / RD {nl['RD']:.1f} / CD {nl['CD']:.1f} / LD {nl['LD']:.1f} / "
        f"RA {nl['RA']:.1f} / CA {nl['CA']:.1f} / LA {nl['LA']:.1f}[br]"
        f"[b]Opponent:[/b] MID {other['MID']:.1f} / RD {other['RD']:.1f} / CD {other['CD']:.1f} / LD {other['LD']:.1f} / "
        f"RA {other['RA']:.1f} / CA {other['CA']:.1f} / LA {other['LA']:.1f}[br][br]"
    )
    return f"{header_block}[table][tr][th]Scenario[/th][th]Your Tactic[/th][th]Opp. Tactic[/th][th]Your Goals[/th][th]Opp. Goals[/th][th]Δ[/th][/tr]{rows_bbcode}[/table]"

def generate_full_roster_html_bbcode(df_db):
    rows_bbcode = ''
    for _, r in df_db.dropna(subset=['Speler']).iterrows():
        rows_bbcode += (
            f"[tr][td]{r.get('PlayerID', '')}[/td][td][b]{r.get('Speler', '')}[/b][/td][td]{r.get('Positie', '')}[/td]"
            f"[td]{r.get('Leeftijd', '')}[/td][td]{r.get('Ervaring', 4.0)}[/td][td]{r.get('Specialiteit', '')}[/td]"
            f"[td]{r.get('HTMS', '')}[/td][td]{r.get('HTMS28', '')}[/td][td]{r.get('GK', 1.0)}[/td][td]{r.get('DE', 5.0)}[/td]"
            f"[td]{r.get('PM', 5.0)}[/td][td]{r.get('WI', 5.0)}[/td][td]{r.get('Pas', 4.0)}[/td][td]{r.get('SC', 5.0)}[/td]"
            f"[td]{r.get('SH', 1.0)}[/td][/tr]"
        )
    return f"[table][tr][th]PlayerID[/th][th]Speler[/th][th]Positie[/th][th]Leeftijd[/th][th]XP[/th][th]Specialiteit[/th][th]HTMS[/th][th]HTMS28[/th][th]GK[/th][th]DE[/th][th]PM[/th][th]WI[/th][th]PAS[/th][th]SC[/th][th]SH[/th][/tr]{rows_bbcode}[/table]"

def generate_app_csv_template():
    valid_positions = list(RICHTSKILLS_DEFAULT.keys())
    sample_data = [{
        'Nationality': 'Netherlands', 'Name': 'Jan Jansen', 'PlayerID': 485123456, 'Specialty': 'Quick', 'Injuries': 0, 'Transfer-listed': '', 'Age': 20, 'Days': 15, 'TSI': 15000, 'Experience': 4, 'Leadership': 5, 'Form': 6.0, 'Stamina': 6.0, 'Matches for the national team': 0, 'Matches for the national U21 team': 0, 'National team player!': 0, 'Positie': 'NFW', 'Wage': 2100, 'Positie_Valid_Options (reference only, leave blank on your rows)': ' / '.join(valid_positions)
    }]
    sample_data.extend([{key: '' for key in sample_data[0].keys()}] * 28)
    return pd.DataFrame(sample_data).to_csv(index=False).encode('utf-8')

def generate_hattrick_csv_template():
    sample_data = [{
        'Nationality': 'Netherlands', 'Name': 'Jan Jansen', 'PlayerID': 485123456, 'Specialty': 'Quick', 'Injuries': 0, 'Transfer-listed': '', 'Age': 20, 'Days': 15, 'TSI': 15000, 'Experience': 4, 'Leadership': 5, 'Form': 6.0, 'Stamina': 6.0, 'Matches for the national team': 0, 'Matches for the national U21 team': 0, 'National team player!': 0
    }]
    sample_data.extend([{key: '' for key in sample_data[0].keys()}] * 28)
    return pd.DataFrame(sample_data).to_csv(index=False).encode('utf-8')

def generate_htp_csv_template():
    htp_cols = [
        'PlayerID', 'FirstName', 'NickName', 'LastName', 'Age', 'AgeDays', 'TSI', 'Salary', 'SalaryAbroad', 
        'InjuryLevel', 'Cards', 'TransferListed', 'OwningUserID', 'OwningTeamID', 'IsAbroad', 'NativeLeagueID', 
        'OwningLeagueID', 'OwningLeagueName', 'IsNationalTeam', 'WasNationalTeam', 'Agreeability', 'Aggressiveness', 
        'Honesty', 'Loyalty', 'Experience', 'Leadership', 'Specialty', 'SpecialtyName', 'PlayerForm', 'StaminaSkill', 
        'KeeperSkill', 'PlaymakerSkill', 'ScorerSkill', 'PassingSkill', 'WingerSkill', 'DefenderSkill', 'SetPiecesSkill', 
        'EtalonID', 'EtalonName', 'Potential', 'DiffTraining', 'TrainingType', 'StaminaTrainingPart', 'TrainingName', 
        'TrainingType_Last', 'StaminaTrainingPart_Last', 'TrainingLevel', 'NewTrainingLevel', 'TrainingLevel_Last', 
        'TrainerSkill', 'TeamTrainerSkill', 'TeamTrainerLeadership', 'AssistantTrainerLevels', 'FormCoachLevels', 
        'MedicLevels', 'MatchID', 'PositionCode', 'PlayerCategoryID', 'PlayerCategoryName', 'MatchTime', 'Rating', 
        'RatingEndOfGame', 'Updated', 'UpdatedSkills', 'OwnerNotes', 'LastScoutNote'
    ]
    return pd.DataFrame(columns=htp_cols).to_csv(index=False, sep=';').encode('utf-8')

def find_col_alias(df, aliases, default=np.nan):
    df_cols_lower = {str(c).strip().lower(): c for c in df.columns}
    found_cols = [df[df_cols_lower[a.strip().lower()]] for a in aliases if a.strip().lower() in df_cols_lower]
    if not found_cols: return pd.Series([default] * len(df))
    res = found_cols[0]
    # (pandas 2.2+: opt in to the future fillna behaviour, so no 'Downcasting object dtype arrays' warning)
    try:
        ctx = pd.option_context('future.no_silent_downcasting', True)
    except (KeyError, pd.errors.OptionError):
        import contextlib
        ctx = contextlib.nullcontext()
    with ctx:
        for col in found_cols[1:]:
            res = res.fillna(col)
        res = res.fillna(default)
    return res.infer_objects()

def clean_num_series(series):
    def clean_val(v):
        if pd.isna(v): return np.nan
        s = str(v).replace('€', '').replace('$', '').replace('\xa0', '').replace(' ', '').strip()
        if not s: return np.nan
        has_comma, has_dot = ',' in s, '.' in s
        if has_comma and has_dot:
            if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.')
            else: s = s.replace(',', '')
        elif has_comma:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) == 3 and not parts[1].startswith('0'): s = s.replace(',', '')
            else: s = s.replace(',', '.')
        return pd.to_numeric(s, errors='coerce')
    return series.apply(clean_val)

_NAME_ALIASES_LOWER = {'name', 'speler', 'naam', 'player name', 'player_name', 'firstname', 'lastname'}
def read_uploaded_csv(uploaded_file):
    import io as _io

    # Read raw bytes and decode
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    for enc in ('utf-8-sig', 'latin1', 'utf-8'):
        try:
            raw = raw_bytes.decode(enc, errors='ignore')
            break
        except Exception:
            continue

    lines = raw.replace('\r\n', '\n').replace('\r', '\n').strip().split('\n')
    if not lines:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file)

    # Detect separator from header
    header = lines[0]
    sep = ','
    for s in [',', ';', '\t']:
        if header.count(s) > header.count(sep if s != sep else ';'):
            sep = s

    n_cols = len(header.split(sep))

    # Fix lines with extra separator caused by commas in country names
    # e.g. "Hong Kong, China,PlayerName,..." → merge first two fields
    fixed = [header]
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(sep)
        if len(parts) == n_cols + 1 and not parts[-1].strip():
            # One extra, empty field at the end (trailing separator): drop it
            fixed.append(sep.join(parts[:-1]))
        elif len(parts) == n_cols + 1:
            # One extra field — merge first two (nationality has comma)
            merged = parts[0].strip() + ', ' + parts[1].strip()
            fixed.append(sep.join([merged] + parts[2:]))
        elif len(parts) >= n_cols - 1:
            # Accept rows with up to 1 fewer column (trailing empty column omitted)
            fixed.append(line)
        # else: skip truly malformed lines

    fixed_str = '\n'.join(fixed)

    try:
        # index_col=False: never use the first column as the row index (rows with one field more than the
        # header made pandas do that, and the duplicate countries then broke the import:
        # "cannot reindex on an axis with duplicate labels")
        df = pd.read_csv(_io.StringIO(fixed_str), sep=sep, engine='python',
                         on_bad_lines='skip', dtype=str, index_col=False)
        # Drop trailing $ column if present
        if len(df.columns) and str(df.columns[-1]).strip() in ('$', ''):
            df = df.iloc[:, :-1]
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    # Fallback: try original file with various separators
    for s in [',', ';', '\t']:
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, sep=s, on_bad_lines='skip',
                             engine='python', encoding='latin1')
            if df.shape[1] > 1:
                return df
        except Exception:
            pass

    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file, on_bad_lines='skip', engine='python',
                       encoding='latin1')

def safe_int(val, default=0): return int(float(val)) if not pd.isna(val) and str(val).strip() not in ('', 'nan', 'NaN', 'None') else default
def safe_float(val, default=0.0): return float(val) if not pd.isna(val) and str(val).strip() not in ('', 'nan', 'NaN', 'None') else default

def _parse_match_dates(series):
    """Match dates as 'YYYY-MM-DD' (Hattrick CSV: 13-10-2026, HTP: 2026-10-17 20:00:00), None if unreadable."""
    out = []
    for v in series.to_numpy():
        s = '' if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
        if not s or s.lower() == 'nan':
            out.append(None)
            continue
        iso = len(s) >= 4 and s[:4].isdigit()          # year first: don't read it day-first
        d = pd.to_datetime(s, errors='coerce', dayfirst=not iso)
        out.append(None if pd.isna(d) else d.strftime('%Y-%m-%d'))
    return out


def import_nt_players_csv(csv_df, username):
    # one row per line, each column once (an .xlsx or an odd CSV can bring a non-unique index / repeated columns)
    df = csv_df.loc[:, ~pd.Index(csv_df.columns).duplicated()].reset_index(drop=True).copy()
    if 'FirstName' in df.columns and 'LastName' in df.columns:
        df['__Name__'] = df['FirstName'].astype(str).replace('nan', '').str.strip() + ' ' + df['LastName'].astype(str).replace('nan', '').str.strip()
    else:
        df['__Name__'] = find_col_alias(df, ['Name', 'Speler', 'Naam', 'Player Name', 'Player_Name'])
        
    df = df.dropna(subset=['__Name__'])
    df = df[df['__Name__'].astype(str).str.strip() != '']
    df = df[df['__Name__'].astype(str).str.strip().str.lower() != 'nan']
    if df.empty: return pd.DataFrame()
    
    out = pd.DataFrame()
    out['username'] = [username] * len(df)
    out['PlayerID'] = clean_num_series(find_col_alias(df, ['PlayerID', 'Player ID', 'SpelerID', 'Speler ID', 'ID'], 0)).fillna(0).astype('int64')
    out['Speler'] = df['__Name__'].astype(str).str.strip()
    out['Positie'] = find_col_alias(df, ['Category', 'Categorie', 'Positie', 'Position', 'POS', 'PositionCode', 'PlayerCategoryName'], '').astype(str).str.strip().map(lambda c: CATEGORY_TO_POSITION.get(c, normalize_position(c) if normalize_position(c) in tuple(RICHTSKILLS_DEFAULT.keys()) else ''))
    out['Leeftijd'] = clean_num_series(find_col_alias(df, ['Age', 'Leeftijd'], 20)).fillna(20).astype(int)
    out['dag(en)'] = clean_num_series(find_col_alias(df, ['Days', 'dag(en)', 'Dagen', 'Day', 'AgeDays'], 0)).fillna(0).astype(int)
    out['Specialiteit'] = find_col_alias(df, ['Specialty', 'Specialiteit', 'Spec', 'SpecialtyName'], 'None').apply(clean_spec)
    out['Vorm'] = clean_num_series(find_col_alias(df, ['Form', 'Vorm', 'Current Form', 'PlayerForm'], 6.0)).fillna(6.0)
    out['Conditie'] = clean_num_series(find_col_alias(df, ['Stamina', 'Conditie', 'Fysiek', 'StaminaSkill'], 6.0)).fillna(6.0)
    out['Ervaring'] = clean_num_series(find_col_alias(df, ['Experience', 'Ervaring', 'Exp', 'XP', 'Ervaring (XP)'], 4.0)).fillna(4.0)
    out['TSI'] = clean_num_series(find_col_alias(df, ['TSI', 'TSI Value'], 1000)).fillna(1000)
    
    # Wage as in the file. The currency is chosen on the import page (default euro); no guessing
    # from the size of the number (a real €90,000 wage used to be divided by 10).
    out['Loon'] = clean_num_series(find_col_alias(df, ['Salary', 'Loon', 'Wage', 'Weekly Wage', 'WAGE'], 1000)).fillna(1000)

    out['Leiderschap'] = clean_num_series(find_col_alias(df, ['Leadership', 'Leiderschap', 'LS'], 5.0)).fillna(5.0)
    out['Nationality'] = find_col_alias(df, ['Nationality', 'Nationaliteit', 'Country', 'OwningLeagueName'], 'Netherlands').astype(str)
    out['Injuries'] = clean_num_series(find_col_alias(df, ['Injuries', 'Blessure', 'InjuryLevel'], 0.0)).fillna(0.0)

    # Playing abroad (HTP: IsAbroad). Empty when the file doesn't say; then the import keeps
    # the flag the player already has.
    def _yes_no(v):
        s = str(v).strip().lower()
        if s in ('1', '1.0', 'true', 'yes', 'ja', 'x', 'y', 'j'):
            return 1
        if s in ('0', '0.0', 'false', 'no', 'nee', 'n'):
            return 0
        return np.nan
    out['Foreign'] = find_col_alias(df, ['IsAbroad', 'Foreign', 'Abroad', 'Buitenland', 'Playing abroad'], np.nan).apply(_yes_no)
    out['Transfer-listed'] = find_col_alias(df, ['Transfer-listed', 'Transferlijst', 'TransferListed'], '').astype(str).replace('nan', '')

    # Last match: Hattrick CSV "Last match position / rating / date", HTP "PositionCode / Rating / MatchTime".
    # Only for the import preview (position check); not written to the database.
    lm_text = find_col_alias(df, ['Last match position'], '').astype(str).to_numpy()
    lm_code = find_col_alias(df, ['PositionCode'], '').astype(str).to_numpy()
    out['_lm_slot'] = [match_slot(t) or match_slot(c) for t, c in zip(lm_text, lm_code)]
    out['_lm_rating'] = [None if pd.isna(v) else float(v) for v in
                         clean_num_series(find_col_alias(df, ['Last match rating', 'Rating'], np.nan)).to_numpy()]
    out['_lm_date'] = _parse_match_dates(find_col_alias(df, ['Last match date', 'MatchTime'], np.nan))
    out['HTMS'] = clean_num_series(find_col_alias(df, ['HTMS', 'HTMS Ability'], np.nan))
    out['HTMS28'] = clean_num_series(find_col_alias(df, ['HTMS28', 'HTMS Potential'], np.nan))

    out['GK'] = clean_num_series(find_col_alias(df, ['GK', 'Keeper', 'KeeperSkill'], 1.0)).fillna(1.0)
    out['DE'] = clean_num_series(find_col_alias(df, ['DE', 'Defending', 'DEF', 'DefenderSkill'], 5.0)).fillna(5.0)
    out['PM'] = clean_num_series(find_col_alias(df, ['PM', 'Playmaking', 'PlaymakerSkill'], 5.0)).fillna(5.0)
    out['WI'] = clean_num_series(find_col_alias(df, ['WI', 'Winger', 'WNG', 'WingerSkill'], 5.0)).fillna(5.0)
    out['Pas'] = clean_num_series(find_col_alias(df, ['Pas', 'Passing', 'PAS', 'PassingSkill'], 4.0)).fillna(4.0)
    out['SC'] = clean_num_series(find_col_alias(df, ['SC', 'Scoring', 'ScorerSkill'], 5.0)).fillna(5.0)
    out['SH'] = clean_num_series(find_col_alias(df, ['SH', 'Set Pieces', 'SP', 'SetPiecesSkill'], 1.0)).fillna(1.0)

    # Track which fields the file actually supplied (vs. placeholder defaults
    # filled in above), so the import preview can flag them and the
    # auto-calculate button knows what it may overwrite.
    def _given(aliases):
        return clean_num_series(find_col_alias(df, aliases, np.nan)).notna().to_numpy()
    tsi_given = _given(['TSI', 'TSI Value'])
    wage_given = _given(['Salary', 'Loon', 'Wage', 'Weekly Wage', 'WAGE'])
    htms_given = _given(['HTMS', 'HTMS Ability'])
    skills_given = np.zeros(len(out), dtype=bool)
    for grp in (['GK', 'Keeper', 'KeeperSkill'], ['DE', 'Defending', 'DEF', 'DefenderSkill'],
                ['PM', 'Playmaking', 'PlaymakerSkill'], ['WI', 'Winger', 'WNG', 'WingerSkill'],
                ['Pas', 'Passing', 'PAS', 'PassingSkill'], ['SC', 'Scoring', 'ScorerSkill'],
                ['SH', 'Set Pieces', 'SP', 'SetPiecesSkill']):
        skills_given |= _given(grp)
    pos_given = np.array([str(p).strip() in RICHTSKILLS_DEFAULT for p in out['Positie'].tolist()])
    missing = []
    for i in range(len(out)):
        m = [name for name, ok in (('Positie', pos_given[i]), ('TSI', tsi_given[i]), ('Loon', wage_given[i]),
                                   ('skills', skills_given[i]), ('HTMS', htms_given[i])) if not ok]
        missing.append(','.join(m))
    out['_missing'] = missing

    blank_pos = out['Positie'].astype(str).str.strip() == ''
    if blank_pos.any():
        out.loc[blank_pos, 'Positie'] = out.loc[blank_pos].apply(
            lambda r: infer_position_from_skills(r['GK'], r['DE'], r['PM'], r['WI'], r['Pas'], r['SC'], r.get('Specialiteit'), sh=r.get('SH')), axis=1)

    def fill_htms_estimates(row):
        htms = row.get('HTMS', np.nan)
        htms28 = row.get('HTMS28', np.nan)
        needs_htms = pd.isna(htms) or htms <= 0
        needs_htms28 = pd.isna(htms28) or htms28 <= 0
        
        if needs_htms or needs_htms28:
            has_real_skills = (
                row.get('GK', 1.0) > 1.0 or row.get('DE', 5.0) > 5.0 or 
                row.get('PM', 5.0) > 5.0 or row.get('WI', 5.0) > 5.0 or 
                row.get('SC', 5.0) > 5.0
            )
            if has_real_skills:
                calc_htms = calculate_htms_ability(
                    row.get('GK',1.0), row.get('DE',5.0), row.get('PM',5.0), 
                    row.get('WI',5.0), row.get('Pas',4.0), row.get('SC',5.0), row.get('SH',1.0)
                )
                if needs_htms: row['HTMS'] = calc_htms
                if needs_htms28: row['HTMS28'] = calculate_htms_potential(row.get('Leeftijd', 20), row.get('dag(en)', 0), calc_htms)
            else:
                est_h, est_h28, _ = estimate_htms_from_profile(
                    age=row.get('Leeftijd', 20), days=row.get('dag(en)', 0), 
                    tsi=row.get('TSI', 1000), wage=row.get('Loon', 1000),
                    form=row.get('Vorm', 6.0), cond=row.get('Conditie', 6.0), 
                    spec=row.get('Specialiteit', 'None'), pos_code=row.get('Positie', 'NFW')
                )
                if needs_htms: row['HTMS'] = est_h
                if needs_htms28: row['HTMS28'] = est_h28
        return row

    # Clean numbers: skills and form/stamina to 3 decimals (files can carry long sublevels).
    for _c in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH'):
        if _c in out.columns:
            out[_c] = pd.to_numeric(out[_c], errors='coerce').round(3)
    for _c, _mx in (('Vorm', 8.0), ('Conditie', 9.4)):     # Hattrick's maxima (stamina: Schum)
        if _c in out.columns:
            out[_c] = pd.to_numeric(out[_c], errors='coerce').clip(upper=_mx).round(3)
    result = out.apply(fill_htms_estimates, axis=1)
    # Which fields the file really contains (so updates of existing players only overwrite those).
    _lower = {str(c).strip().lower() for c in df.columns}
    def _has(aliases):
        return any(a.strip().lower() in _lower for a in aliases)
    _present_map = {
        'Positie': ['Category', 'Categorie', 'Positie', 'Position', 'POS', 'PositionCode', 'PlayerCategoryName'],
        'Leeftijd': ['Age', 'Leeftijd'], 'dag(en)': ['Days', 'dag(en)', 'Dagen', 'Day', 'AgeDays'],
        'Specialiteit': ['Specialty', 'Specialiteit', 'Spec', 'SpecialtyName'],
        'Vorm': ['Form', 'Vorm', 'Current Form', 'PlayerForm'], 'Conditie': ['Stamina', 'Conditie', 'Fysiek', 'StaminaSkill'],
        'Ervaring': ['Experience', 'Ervaring', 'Exp', 'XP', 'Ervaring (XP)'], 'TSI': ['TSI', 'TSI Value'],
        'Loon': ['Salary', 'Loon', 'Wage', 'Weekly Wage', 'WAGE'], 'Leiderschap': ['Leadership', 'Leiderschap', 'LS'],
        'Nationality': ['Nationality', 'Nationaliteit', 'Country', 'OwningLeagueName'],
        'Injuries': ['Injuries', 'Blessure', 'InjuryLevel'], 'Transfer-listed': ['Transfer-listed', 'Transferlijst', 'TransferListed'],
        'HTMS': ['HTMS', 'HTMS Ability'], 'HTMS28': ['HTMS28', 'HTMS Potential'],
        'Foreign': ['IsAbroad', 'Foreign', 'Abroad', 'Buitenland', 'Playing abroad'],
        'skills': ['GK', 'Keeper', 'KeeperSkill', 'DE', 'Defending', 'DEF', 'DefenderSkill', 'PM', 'Playmaking',
                   'PlaymakerSkill', 'WI', 'Winger', 'WNG', 'WingerSkill', 'Pas', 'Passing', 'PAS', 'PassingSkill',
                   'SC', 'Scoring', 'ScorerSkill', 'SH', 'Set Pieces', 'SP', 'SetPiecesSkill'],
    }
    result.attrs['present'] = sorted(k for k, al in _present_map.items() if _has(al))
    return result

# ==============================================================================
# 3. REFERENCE PLAYER DATABASE
# ==============================================================================
REFERENCE_PLAYER_COLS = ['PlayerID', 'Speler', 'Nationality', 'Positie', 'Specialiteit', 'Leeftijd', 'dag(en)', 'TSI', 'Loon', 'HTMS', 'HTMS28', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH']

REFERENCE_DEFAULT_SKILLS = {'GK': 1.0, 'DE': 5.0, 'PM': 5.0, 'WI': 5.0, 'Pas': 4.0, 'SC': 5.0, 'SH': 1.0}


def build_reference_rows_from_roster_df(df):
    """Reference rows from roster/import rows. Rows that are not real data are left out: missing skills,
    TSI or wage, or skills that are exactly the import defaults (GK1 DE5 PM5 WI5 Pas4 SC5 SH1)."""
    if df is None or df.empty: return pd.DataFrame(columns=REFERENCE_PLAYER_COLS)
    out = pd.DataFrame()
    for col in REFERENCE_PLAYER_COLS:
        out[col] = df[col] if col in df.columns else np.nan
    sk_raw = pd.DataFrame({sk: clean_num_series(out[sk]) for sk in REFERENCE_DEFAULT_SKILLS})
    missing = sk_raw[['DE', 'PM', 'WI', 'Pas', 'SC']].isna().any(axis=1)
    is_default = pd.Series(True, index=out.index)
    for sk, v in REFERENCE_DEFAULT_SKILLS.items():
        is_default &= sk_raw[sk].round(3).eq(v)
    tsi_raw, wage_raw = clean_num_series(out['TSI']), clean_num_series(out['Loon'])
    no_numbers = tsi_raw.isna() | wage_raw.isna() | ((tsi_raw == 1000) & (wage_raw == 1000)) | (wage_raw == 1000)
    out = out[~(missing | is_default | no_numbers)].copy()
    if out.empty: return pd.DataFrame(columns=REFERENCE_PLAYER_COLS)
    out['PlayerID'] = clean_num_series(out['PlayerID']).fillna(0).astype('int64')
    out['Speler'] = out['Speler'].fillna('Unknown').astype(str)
    out['Nationality'] = out['Nationality'].fillna('Netherlands').astype(str)
    out['Positie'] = out['Positie'].fillna('').astype(str)
    out['Specialiteit'] = out['Specialiteit'].fillna('None').astype(str)
    out['Leeftijd'] = clean_num_series(out['Leeftijd']).fillna(20).astype(int)
    out['dag(en)'] = clean_num_series(out['dag(en)']).fillna(0).astype(int)
    for sk, default in [('GK', 1.0), ('DE', 5.0), ('PM', 5.0), ('WI', 5.0), ('Pas', 4.0), ('SC', 5.0), ('SH', 1.0)]:
        out[sk] = clean_num_series(out[sk]).fillna(default)
    out['Positie'] = out.apply(lambda r: r['Positie'] if r['Positie'] in RICHTSKILLS_DEFAULT else infer_position_from_skills(r['GK'], r['DE'], r['PM'], r['WI'], r['Pas'], r['SC'], r['Specialiteit'], sh=r['SH']), axis=1)
    # A 'SHWB' without set pieces is a normal wing back (the bulk import stored 163 of them).
    out.loc[(out['Positie'] == 'SHWB') & (out['SH'] < 8.0), 'Positie'] = 'NWB'
    out['TSI'] = clean_num_series(out['TSI']).fillna(1000)
    out['Loon'] = clean_num_series(out['Loon']).fillna(1000)
    computed_htms = out.apply(lambda r: calculate_htms_ability(r['GK'], r['DE'], r['PM'], r['WI'], r['Pas'], r['SC'], r['SH']), axis=1)
    out['HTMS'] = clean_num_series(out['HTMS']).where(lambda s: s.notna() & (s > 0), computed_htms)
    computed_htms28 = out.apply(lambda r: calculate_htms_potential(r['Leeftijd'], r['dag(en)'], r['HTMS']), axis=1)
    out['HTMS28'] = clean_num_series(out['HTMS28']).where(lambda s: s.notna() & (s > 0), computed_htms28)
    return out[out['Positie'].isin(RICHTSKILLS_DEFAULT.keys())].reset_index(drop=True)

def add_players_to_reference_db(df, source='import', added_by='admin'):
    ref_rows = build_reference_rows_from_roster_df(df)
    if ref_rows.empty: return 0
    conn = get_db_connection()
    cursor = conn.cursor()
    existing = set(cursor.execute('SELECT PlayerID, Leeftijd, "dag(en)" FROM reference_players WHERE PlayerID != 0;').fetchall())
    added_date = pd.Timestamp.now('UTC').isoformat()
    inserted = 0
    for _, r in ref_rows.iterrows():
        key = (int(r['PlayerID']), int(r['Leeftijd']), int(r['dag(en)']))
        if r['PlayerID'] != 0 and key in existing: continue
        cursor.execute(
            'INSERT INTO reference_players (PlayerID, Speler, Nationality, Positie, Specialiteit, Leeftijd, "dag(en)", TSI, Loon, HTMS, HTMS28, GK, DE, PM, WI, Pas, SC, SH, source, added_by, added_date) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            (int(r['PlayerID']), r['Speler'], r['Nationality'], r['Positie'], r['Specialiteit'], int(r['Leeftijd']), int(r['dag(en)']),
             float(r['TSI']), float(r['Loon']), float(r['HTMS']), float(r['HTMS28']), float(r['GK']), float(r['DE']), float(r['PM']),
             float(r['WI']), float(r['Pas']), float(r['SC']), float(r['SH']), source, added_by, added_date)
        )
        existing.add(key)
        inserted += 1
    conn.commit(); conn.close()
    get_reference_players_df.clear()
    return inserted

def sync_player_to_reference_db(player_row, username, source='manual_update'):
    """Upserts ONE player's current skills into the Reference DB, matched on
    PlayerID (+ Age/Days), falling back to Speler name (+ Age/Days) when there
    is no PlayerID. Unlike add_players_to_reference_db (import-time, insert-only,
    skips anything that already exists), this UPDATES a matching row in place —
    it's meant to be called after skills are corrected/solved in the Estimator
    or Auto-Solver, so the Reference DB stops sitting on stale import-time
    guesses once you know a player's real numbers.
    Returns 'updated', 'inserted', or 'skipped' (row didn't parse to a valid position).
    """
    ref_rows = build_reference_rows_from_roster_df(pd.DataFrame([player_row]))
    if ref_rows.empty:
        return 'skipped'
    r = ref_rows.iloc[0]
    pid = int(r['PlayerID'])
    age, days = int(r['Leeftijd']), int(r['dag(en)'])
    added_date = pd.Timestamp.now('UTC').isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    match = None
    if pid:
        match = cursor.execute(
            'SELECT id FROM reference_players WHERE PlayerID=? AND Leeftijd=? AND "dag(en)"=?;',
            (pid, age, days)).fetchone()
    if match is None:
        match = cursor.execute(
            'SELECT id FROM reference_players WHERE PlayerID=0 AND Speler=? AND Leeftijd=? AND "dag(en)"=?;',
            (str(r['Speler']), age, days)).fetchone()

    if match is not None:
        cursor.execute(
            'UPDATE reference_players SET Speler=?, Nationality=?, Positie=?, Specialiteit=?, TSI=?, Loon=?, '
            'HTMS=?, HTMS28=?, GK=?, DE=?, PM=?, WI=?, Pas=?, SC=?, SH=?, source=?, added_by=?, added_date=? '
            'WHERE id=?;',
            (r['Speler'], r['Nationality'], r['Positie'], r['Specialiteit'], float(r['TSI']), float(r['Loon']),
             float(r['HTMS']), float(r['HTMS28']), float(r['GK']), float(r['DE']), float(r['PM']), float(r['WI']),
             float(r['Pas']), float(r['SC']), float(r['SH']), source, username, added_date, match[0])
        )
        result = 'updated'
    else:
        cursor.execute(
            'INSERT INTO reference_players (PlayerID, Speler, Nationality, Positie, Specialiteit, Leeftijd, "dag(en)", TSI, Loon, HTMS, HTMS28, GK, DE, PM, WI, Pas, SC, SH, source, added_by, added_date) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            (pid, r['Speler'], r['Nationality'], r['Positie'], r['Specialiteit'], age, days,
             float(r['TSI']), float(r['Loon']), float(r['HTMS']), float(r['HTMS28']), float(r['GK']), float(r['DE']),
             float(r['PM']), float(r['WI']), float(r['Pas']), float(r['SC']), float(r['SH']), source, username, added_date)
        )
        result = 'inserted'

    conn.commit(); conn.close()
    get_reference_players_df.clear()
    return result

@cache_data(ttl=30)
def get_reference_players_df():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reference_players;')
    rows = cursor.fetchall()
    col_names = [d[0] for d in cursor.description]
    df = pd.DataFrame(rows, columns=col_names)
    conn.close()
    return df

REFERENCE_EDIT_COLS = ['PlayerID', 'Speler', 'Nationality', 'Positie', 'Specialiteit', 'Leeftijd', 'dag(en)', 'TSI',
                       'Loon', 'HTMS', 'HTMS28', 'GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH', 'Foreign']


def update_reference_player(row_id, values):
    """Update one reference player (by its row id) with the given column values."""
    vals = {k: v for k, v in values.items() if k in REFERENCE_EDIT_COLS}
    if not vals:
        return
    sets = ', '.join(f'"{k}"=?' for k in vals)
    conn = get_db_connection()
    conn.cursor().execute(f'UPDATE reference_players SET {sets} WHERE id=?;', (*vals.values(), int(row_id)))
    conn.commit(); conn.close()
    get_reference_players_df.clear()


def set_reference_abroad(row_ids, abroad):
    """Mark reference players as playing abroad (wage includes +20%) or not."""
    ids = [int(i) for i in row_ids]
    if not ids:
        return
    conn = get_db_connection()
    conn.cursor().execute(f'UPDATE reference_players SET "Foreign"=? WHERE id IN ({",".join("?" * len(ids))});', (1 if abroad else 0, *ids))
    conn.commit(); conn.close()
    get_reference_players_df.clear()


def reference_likely_abroad(df):
    """Row ids of reference players under 28, not marked abroad, whose wage is more than 8% above
    what their known skills give today: skills only rise after the birthday, so only Hattrick's
    +20% abroad bonus can explain that."""
    out = []
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        try:
            if int(float(r.get('Foreign') or 0)) == 1 or int(float(r.get('Leeftijd') or 99)) >= 28:
                continue
            sk = [float(r.get(k) or 1.0) for k in ('GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH')]
            exp = calculate_exact(int(r['Leeftijd']), 0, r.get('Specialiteit') or 'None', 6, 6, *sk)[3]
            if float(r.get('Loon') or 0) > exp * 1.08:
                out.append(r['id'])
        except Exception:
            continue
    return out


def set_reference_position(row_ids, position):
    """Give several reference players the same position."""
    ids = [int(i) for i in row_ids]
    if not ids:
        return
    conn = get_db_connection()
    conn.cursor().execute(f'UPDATE reference_players SET Positie=? WHERE id IN ({",".join("?" * len(ids))});', (position, *ids))
    conn.commit(); conn.close()
    get_reference_players_df.clear()


REESTIMATE_COLS = ['GK', 'DE', 'PM', 'WI', 'Pas', 'SC', 'SH', 'source']


def apply_reference_reestimate(updates, username='admin'):
    """updates: [(row id, {skill: value})]. Saves the old values first (one batch), then writes the new skills
    with source 'all_combos'. Returns the number of rows changed."""
    import json
    if not updates:
        return 0
    df = get_reference_players_df()
    old = {int(r['id']): r for _, r in df.iterrows()}
    batch = pd.Timestamp.now('UTC').isoformat()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS reference_backup (id INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT NOT NULL, ref_id INTEGER NOT NULL, data_json TEXT, saved_at TEXT);')
    n = 0
    for rid, vals in updates:
        rid = int(rid)
        if rid not in old:
            continue
        prev = {c: (None if pd.isna(old[rid].get(c)) else (float(old[rid].get(c)) if c != 'source' else str(old[rid].get(c))))
                for c in REESTIMATE_COLS if c in old[rid]}
        cur.execute('INSERT INTO reference_backup (batch, ref_id, data_json, saved_at) VALUES (?, ?, ?, ?);',
                    (batch, rid, json.dumps(prev), batch))
        new = {k: float(v) for k, v in vals.items() if k in REESTIMATE_COLS and k != 'source'}
        new['source'] = 'all_combos'
        sets = ', '.join(f'"{k}"=?' for k in new)
        cur.execute(f'UPDATE reference_players SET {sets}, added_by=? WHERE id=?;', (*new.values(), username, rid))
        n += 1
    conn.commit(); conn.close()
    get_reference_players_df.clear()
    return n


def last_reference_reestimate():
    """(batch, number of rows) of the most recent re-estimate that can still be undone, or None."""
    try:
        conn = get_db_connection()
        row = conn.cursor().execute('SELECT batch, COUNT(*) FROM reference_backup GROUP BY batch ORDER BY batch DESC LIMIT 1;').fetchone()
        conn.close()
        return (row[0], int(row[1])) if row else None
    except Exception:
        return None


def undo_reference_reestimate():
    """Put back the values from before the most recent re-estimate. Returns the number of rows restored."""
    import json
    last = last_reference_reestimate()
    if not last:
        return 0
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute('SELECT ref_id, data_json FROM reference_backup WHERE batch=?;', (last[0],)).fetchall()
    n = 0
    for rid, js in rows:
        prev = json.loads(js or '{}')
        if not prev:
            continue
        sets = ', '.join(f'"{k}"=?' for k in prev)
        cur.execute(f'UPDATE reference_players SET {sets} WHERE id=?;', (*prev.values(), int(rid)))
        n += 1
    cur.execute('DELETE FROM reference_backup WHERE batch=?;', (last[0],))
    conn.commit(); conn.close()
    get_reference_players_df.clear()
    return n


def delete_reference_players(row_ids):
    ids = [int(i) for i in row_ids]
    if not ids:
        return
    conn = get_db_connection()
    conn.cursor().execute(f'DELETE FROM reference_players WHERE id IN ({",".join("?" * len(ids))});', ids)
    conn.commit(); conn.close()
    get_reference_players_df.clear()


def get_reference_players_count():
    return len(get_reference_players_df())

def clear_reference_players_db():
    conn = get_db_connection()
    conn.cursor().execute('DELETE FROM reference_players;')
    conn.commit(); conn.close()
    get_reference_players_df.clear()

def import_reference_players_file(df):
    parsed = import_nt_players_csv(df, 'reference')
    if parsed.empty: return 0
    return add_players_to_reference_db(parsed, source='bulk_csv', added_by='admin')

def find_similar_players(position, age, spec=None, tsi=None, htms=None, htms28=None, wage=None, k=10, exclude_player_id=None):
    pool = get_reference_players_df()
    if pool.empty: return pool
    if exclude_player_id: pool = pool[pool['PlayerID'] != int(exclude_player_id)]
    if pool.empty: return pool

    same_pos = pool[pool['Positie'] == position].copy()
    pool = same_pos if not same_pos.empty else pool.copy()
    if pool.empty: return pool
    pool['position_match'] = pool['Positie'] == position

    def _scale(series, floor=1.0):
        s = series.astype(float)
        return max(float(s.max() - s.min()), floor)

    dist = pd.Series(0.0, index=pool.index)
    weighted_fields = [('Leeftijd', age, 1.2), ('TSI', tsi, 1.0), ('Loon', wage, 0.6), ('HTMS', htms, 1.5), ('HTMS28', htms28, 1.0)]
    total_weight = 0.0
    for col, target, weight in weighted_fields:
        if target is None: continue
        scale = _scale(pool[col])
        dist = dist + weight * ((pool[col].astype(float) - float(target)) / scale) ** 2
        total_weight += weight
    if total_weight > 0: dist = (dist / total_weight) ** 0.5

    if spec and spec != 'None': dist = dist + np.where(pool['Specialiteit'] == spec, 0.0, 0.35)
    dist = dist + np.where(pool['position_match'], 0.0, 5.0)

    pool['distance'] = dist
    pool = pool.sort_values('distance').head(k).reset_index(drop=True)
    max_d = float(pool['distance'].max()) or 1.0
    pool['match_score'] = (100 * (1 - pool['distance'] / (max_d * 1.15))).clip(lower=0).round(1)
    return pool.drop(columns=['distance', 'id'], errors='ignore')

# ── Watchlist functions ────────────────────────────────────────────────────────

def get_watchlists(username: str) -> dict:
    """Returns {list_name: [player_name, ...]} for a user."""
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT list_name, player_name FROM watchlists WHERE LOWER(username)=LOWER(?) ORDER BY list_name, player_name',
        (username,)
    ).fetchall()
    conn.close()
    result = {}
    for list_name, player_name in rows:
        result.setdefault(list_name, []).append(player_name)
    return result


def create_watchlist(username: str, list_name: str) -> bool:
    """Create an empty watchlist. Returns False if already exists."""
    conn = get_db_connection()
    existing = conn.execute(
        'SELECT 1 FROM watchlists WHERE LOWER(username)=LOWER(?) AND list_name=? LIMIT 1',
        (username, list_name)
    ).fetchone()
    if existing:
        conn.close()
        return False
    # Insert a sentinel row so list exists even if empty
    conn.execute(
        'INSERT OR IGNORE INTO watchlists (username, list_name, player_name) VALUES (?,?,?)',
        (username, list_name, '__EMPTY__')
    )
    conn.commit()
    conn.close()
    return True


def add_to_watchlist(username: str, list_name: str, player_name: str) -> bool:
    conn = get_db_connection()
    # Remove sentinel if present
    conn.execute(
        'DELETE FROM watchlists WHERE LOWER(username)=LOWER(?) AND list_name=? AND player_name=?',
        (username, list_name, '__EMPTY__')
    )
    try:
        conn.execute(
            'INSERT OR IGNORE INTO watchlists (username, list_name, player_name) VALUES (?,?,?)',
            (username, list_name, player_name)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def remove_from_watchlist(username: str, list_name: str, player_name: str):
    conn = get_db_connection()
    conn.execute(
        'DELETE FROM watchlists WHERE LOWER(username)=LOWER(?) AND list_name=? AND player_name=?',
        (username, list_name, player_name)
    )
    # Keep the list when its last player is removed (an empty list is still a list).
    left = conn.execute('SELECT 1 FROM watchlists WHERE LOWER(username)=LOWER(?) AND list_name=? LIMIT 1',
                        (username, list_name)).fetchone()
    if not left:
        conn.execute('INSERT OR IGNORE INTO watchlists (username, list_name, player_name) VALUES (?,?,?)',
                     (username, list_name, '__EMPTY__'))
    conn.commit()
    conn.close()


def delete_watchlist(username: str, list_name: str):
    conn = get_db_connection()
    conn.execute(
        'DELETE FROM watchlists WHERE LOWER(username)=LOWER(?) AND list_name=?',
        (username, list_name)
    )
    conn.commit()
    conn.close()


def rename_watchlist(username: str, old_name: str, new_name: str) -> bool:
    new_name = str(new_name or '').strip()
    if not new_name or new_name == old_name:
        return False
    conn = get_db_connection()
    if conn.execute('SELECT 1 FROM watchlists WHERE LOWER(username)=LOWER(?) AND list_name=? LIMIT 1',
                    (username, new_name)).fetchone():
        conn.close()
        return False   # a list with that name exists already
    try:
        conn.execute(
            'UPDATE watchlists SET list_name=? WHERE LOWER(username)=LOWER(?) AND list_name=?',
            (new_name, username, old_name)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


# ==============================================================================
# Saved lineups (named) — Lineup Simulator -> Score Predictor
# ==============================================================================
def get_user_pref(username, key, default=None):
    """A per-user setting stored in the database (follows the user to every device)."""
    import json
    try:
        conn = get_db_connection()
        conn.execute('CREATE TABLE IF NOT EXISTS user_prefs (username TEXT NOT NULL, pref_key TEXT NOT NULL, value_json TEXT, '
                     'PRIMARY KEY (username, pref_key));')
        row = conn.execute('SELECT value_json FROM user_prefs WHERE LOWER(username)=LOWER(?) AND pref_key=?;',
                           (username, key)).fetchone()
        conn.close()
        return json.loads(row[0]) if row and row[0] is not None else default
    except Exception:
        return default


def set_user_pref(username, key, value):
    import json
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS user_prefs (username TEXT NOT NULL, pref_key TEXT NOT NULL, value_json TEXT, '
                 'PRIMARY KEY (username, pref_key));')
    conn.execute('INSERT OR REPLACE INTO user_prefs (username, pref_key, value_json) VALUES (?, ?, ?);',
                 (str(username).lower(), key, json.dumps(value)))
    conn.commit()
    conn.close()


def save_named_lineup(username, name, data):
    """Store (or overwrite) a named lineup: dict with slots, subs, formation, context, ratings."""
    import json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM saved_lineups WHERE LOWER(username)=LOWER(?) AND name=?;', (username, name))
    cur.execute('INSERT INTO saved_lineups (username, name, saved_at, data_json) VALUES (?,?,?,?);',
                (username, name, pd.Timestamp.utcnow().strftime('%Y-%m-%d %H:%M'), json.dumps(data)))
    conn.commit()
    conn.close()


def get_saved_lineups(username):
    """{name: {'saved_at': ..., **data}}, newest first."""
    import json
    conn = get_db_connection()
    rows = conn.cursor().execute('SELECT name, saved_at, data_json FROM saved_lineups WHERE LOWER(username)=LOWER(?) '
                                 'ORDER BY saved_at DESC, id DESC;', (username,)).fetchall()
    conn.close()
    out = {}
    for name, saved_at, js in rows:
        try:
            out[name] = dict(json.loads(js or '{}'), saved_at=saved_at)
        except Exception:
            continue
    return out


def delete_saved_lineup(username, name):
    conn = get_db_connection()
    conn.cursor().execute('DELETE FROM saved_lineups WHERE LOWER(username)=LOWER(?) AND name=?;', (username, name))
    conn.commit()
    conn.close()


# --- Saved Score Predictor setups (both teams + the opponent's formation mix) ---
def save_prediction(username, name, data):
    """Save (or overwrite) a named Score Predictor setup for this user."""
    import json
    from datetime import datetime
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM saved_predictions WHERE LOWER(username)=LOWER(?) AND name=?;', (username, name))
    cur.execute('INSERT INTO saved_predictions (username, name, saved_at, data_json) VALUES (?,?,?,?);',
                (username, name, datetime.now().strftime('%Y-%m-%d %H:%M'), json.dumps(data)))
    conn.commit()
    conn.close()


def get_saved_predictions(username):
    """{name: {'saved_at': ..., **data}}, newest first."""
    import json
    conn = get_db_connection()
    rows = conn.cursor().execute('SELECT name, saved_at, data_json FROM saved_predictions WHERE LOWER(username)=LOWER(?) '
                                 'ORDER BY saved_at DESC, id DESC;', (username,)).fetchall()
    conn.close()
    out = {}
    for name, saved_at, js in rows:
        try:
            out[name] = dict(json.loads(js or '{}'), saved_at=saved_at)
        except Exception:
            continue
    return out


def delete_saved_prediction(username, name):
    conn = get_db_connection()
    conn.cursor().execute('DELETE FROM saved_predictions WHERE LOWER(username)=LOWER(?) AND name=?;', (username, name))
    conn.commit()
    conn.close()