#!/usr/bin/env python3
"""BITFIN Arena — accounts, sessions, password hashing, and API-key encryption.

- Passwords: scrypt with a per-user salt (stdlib hashlib).
- Tenant AI keys: encrypted at rest with Fernet; the master key lives in a
  chmod-600 file outside the DB and git (ARENA_KEYFILE).
- Sessions: random opaque tokens in the sessions table, 7-day expiry.
- Admin: emails in ADMIN_EMAILS get the admin role at signup.
"""
import os, sqlite3, hashlib, hmac, secrets, base64, time
from cryptography.fernet import Fernet

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'arena.db')
KEYFILE = os.environ.get('ARENA_KEYFILE', '/opt/quant/.arena_key')
ADMIN_EMAILS = set(e.strip().lower() for e in os.environ.get('ADMIN_EMAILS', '').split(',') if e.strip())

def _master():
    if not os.path.exists(KEYFILE):
        k = Fernet.generate_key()
        fd = os.open(KEYFILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.write(fd, k); os.close(fd); return k
    return open(KEYFILE, 'rb').read().strip()
_F = Fernet(_master())
def enc(s): return _F.encrypt(s.encode()).decode() if s else ''
def dec(s):
    try: return _F.decrypt(s.encode()).decode() if s else ''
    except Exception: return ''

def hash_pw(pw):
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(h).decode()
def verify_pw(pw, stored):
    try:
        _, s, h = stored.split('$'); salt = base64.b64decode(s); exp = base64.b64decode(h)
        got = hashlib.scrypt(pw.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(got, exp)
    except Exception: return False

def db(): c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
def _now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def init_auth():
    c = db(); c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, pw_hash TEXT,
      role TEXT DEFAULT 'user', disabled INTEGER DEFAULT 0, created TEXT, last_login TEXT);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER, created REAL, expires REAL);
    """)
    cols = [r[1] for r in c.execute("PRAGMA table_info(tenants)")]
    if 'user_id' not in cols: c.execute("ALTER TABLE tenants ADD COLUMN user_id INTEGER")
    c.commit(); c.close()

def signup(email, pw):
    email = (email or '').strip().lower()
    if '@' not in email or len(pw or '') < 6: return None, 'valid email + password (6+ chars) required'
    c = db()
    if c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone(): c.close(); return None, 'email already registered'
    role = 'admin' if email in ADMIN_EMAILS else 'user'
    c.execute("INSERT INTO users(email,pw_hash,role,created,last_login) VALUES(?,?,?,?,?)",
              (email, hash_pw(pw), role, _now(), _now()))
    c.commit(); uid = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]; c.close()
    return uid, None

def login(email, pw):
    email = (email or '').strip().lower(); c = db()
    u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not u or u['disabled'] or not verify_pw(pw, u['pw_hash']): c.close(); return None
    c.execute("UPDATE users SET last_login=? WHERE id=?", (_now(), u['id'])); c.commit(); c.close()
    return u['id']

def new_session(uid):
    tok = secrets.token_urlsafe(32); now = time.time(); c = db()
    c.execute("INSERT INTO sessions(token,user_id,created,expires) VALUES(?,?,?,?)", (tok, uid, now, now + 7 * 86400))
    c.commit(); c.close(); return tok

def user_by_session(tok):
    if not tok: return None
    c = db(); r = c.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?",
                            (tok, time.time())).fetchone(); c.close()
    return dict(r) if r else None

def logout(tok):
    c = db(); c.execute("DELETE FROM sessions WHERE token=?", (tok,)); c.commit(); c.close()

# ---- rate limiting (in-memory, per key) ----
_HITS = {}
def rate_ok(key, limit, window):
    now = time.time(); q = [t for t in _HITS.get(key, []) if now - t < window]
    if len(q) >= limit: _HITS[key] = q; return False
    q.append(now); _HITS[key] = q; return True

# ---- admin ----
def list_users():
    c = db(); rows = [dict(r) for r in c.execute(
        "SELECT u.id,u.email,u.role,u.disabled,u.created,u.last_login,"
        "(SELECT COUNT(*) FROM tenants t WHERE t.user_id=u.id) n_books FROM users u ORDER BY u.id")]
    c.close(); return rows
def set_disabled(uid, val):
    c = db(); c.execute("UPDATE users SET disabled=? WHERE id=?", (1 if val else 0, uid)); c.commit(); c.close()
