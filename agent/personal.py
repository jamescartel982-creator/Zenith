"""Local password accounts, expiring sessions, and user-owned explicit memories."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from uuid import uuid4


class PersonalStore:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS login_sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS conversation_owners (session_id TEXT PRIMARY KEY, user_id TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, content TEXT NOT NULL, created REAL NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS memories_owner ON memories(user_id, created)')

    @staticmethod
    def password_hash(password, salt):
        return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 600000).hex()

    def register(self, username, display_name, password):
        username = username.strip().casefold()
        display_name = display_name.strip()
        if not re.fullmatch(r'[a-z0-9_-]{3,40}', username):
            raise ValueError('Username needs 3–40 letters, numbers, underscores or hyphens')
        if not 1 <= len(display_name) <= 60 or any(ord(c) < 32 for c in display_name):
            raise ValueError('Choose a display name of 1–60 characters')
        if not 12 <= len(password) <= 256:
            raise ValueError('Choose a password of 12–256 characters')
        salt = secrets.token_hex(16)
        identifier = str(uuid4())
        try:
            with self.store.connect() as db:
                db.execute('INSERT INTO users VALUES (?, ?, ?, ?, ?)', (identifier, username, display_name, salt, self.password_hash(password, salt)))
        except sqlite3.IntegrityError as exc:
            raise ValueError('That username is unavailable') from exc
        return {'id': identifier, 'username': username, 'display_name': display_name}

    def login(self, username, password):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username.strip().casefold(),)).fetchone()
        # Equal-cost hash for absent usernames avoids an obvious account timing leak.
        candidate = self.password_hash(password, row['salt'] if row else '0' * 32)
        if row is None or not hmac.compare_digest(row['password_hash'], candidate):
            return None
        return {key: row[key] for key in ('id', 'username', 'display_name')}

    def issue_session(self, user_id):
        token = secrets.token_urlsafe(32)
        with self.store.connect() as db:
            db.execute('DELETE FROM login_sessions WHERE expires<=?', (time.time(),))
            db.execute('INSERT INTO login_sessions VALUES (?, ?, ?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time() + 7 * 86400))
        return token

    def user_for_token(self, token):
        if not token or len(token) > 128:
            return None
        with self.store.connect() as db:
            row = db.execute('SELECT users.id, username, display_name FROM login_sessions JOIN users ON users.id=login_sessions.user_id WHERE token_hash=? AND expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        return dict(row) if row else None

    def logout(self, token):
        with self.store.connect() as db:
            db.execute('DELETE FROM login_sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
            db.execute('DELETE FROM skill_activations WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def conversation_access(self, session_id, user_id='', create=False):
        with self.store.connect() as db:
            row = db.execute('SELECT user_id FROM conversation_owners WHERE session_id=?', (session_id,)).fetchone()
            if row:
                return row['user_id'] == user_id
            # Legacy conversations remain local/anonymous; signing in cannot claim them.
            legacy = db.execute('SELECT 1 FROM turns WHERE session_id=? LIMIT 1', (session_id,)).fetchone()
            if legacy:
                return not user_id
            if create:
                db.execute('INSERT OR IGNORE INTO conversation_owners VALUES (?, ?)', (session_id, user_id))
                owner = db.execute('SELECT user_id FROM conversation_owners WHERE session_id=?', (session_id,)).fetchone()
                return owner['user_id'] == user_id
            return True  # An unused UUID has no history to disclose.

    def conversations(self, user_id):
        with self.store.connect() as db:
            rows = db.execute('''SELECT t.session_id, MIN(t.created_at) AS created_at,
                MAX(t.created_at) AS updated_at, COUNT(*) AS turns,
                (SELECT prompt FROM turns first WHERE first.session_id=t.session_id ORDER BY rowid LIMIT 1) AS title
                FROM turns t JOIN conversation_owners o ON o.session_id=t.session_id
                WHERE o.user_id=? GROUP BY t.session_id ORDER BY updated_at DESC LIMIT 50''', (user_id,)).fetchall()
        return [dict(row) | {'title': row['title'][:80]} for row in rows]

    def memories(self, user_id):
        with self.store.connect() as db:
            return [dict(row) for row in db.execute('SELECT id, content, created FROM memories WHERE user_id=? ORDER BY created LIMIT 50', (user_id,))]

    def remember(self, user_id, content):
        from .assurance import normalize_input
        content = normalize_input(content)
        if not 1 <= len(content) <= 500:
            raise ValueError('A memory must have 1–500 characters')
        with self.store.connect() as db:
            if db.execute('SELECT COUNT(*) FROM memories WHERE user_id=?', (user_id,)).fetchone()[0] >= 50:
                raise ValueError('You have 50 memories. Remove one before adding another.')
            identifier = str(uuid4())
            db.execute('INSERT INTO memories VALUES (?, ?, ?, ?)', (identifier, user_id, content, time.time()))
        return identifier

    def context_memories(self, user_id, query, max_chars=1200):
        terms = set(re.findall(r'\w{3,}', query.casefold()))
        notes = self.memories(user_id)
        notes.sort(key=lambda note: (len(terms & set(re.findall(r'\w{3,}', note['content'].casefold()))), note['created']), reverse=True)
        selected, used = [], 0
        for note in notes:
            if len(selected) >= 8:
                break
            if used + len(note['content']) <= max_chars:
                selected.append(note)
                used += len(note['content'])
        return selected

    def forget(self, user_id, identifier=None):
        with self.store.connect() as db:
            if identifier:
                return db.execute('DELETE FROM memories WHERE id=? AND user_id=?', (identifier, user_id)).rowcount
            return db.execute('DELETE FROM memories WHERE user_id=?', (user_id,)).rowcount

    def request_human_review(self,user_id,session_id,turn_id,reason):
        if not reason.strip():raise ValueError('Enter a review reason')
        if not self.conversation_access(session_id,user_id):raise ValueError('Conversation not found')
        identifier=str(uuid4())
        with self.store.connect() as db:
            if not db.execute('SELECT 1 FROM turns WHERE id=? AND session_id=?',(turn_id,session_id)).fetchone():raise ValueError('Turn not found')
            previous=db.execute('SELECT id FROM human_reviews WHERE user_id=? AND turn_id=?',(user_id,turn_id)).fetchone()
            if previous:return previous['id']
            if db.execute("SELECT COUNT(*) FROM human_reviews WHERE user_id=? AND status='open'",(user_id,)).fetchone()[0]>=100:raise ValueError('Review request limit reached')
            db.execute("INSERT INTO human_reviews VALUES (?, ?, ?, ?, ?, 'open', '', ?)",(identifier,user_id,session_id,turn_id,reason,time.time()))
        return identifier

    def review_requests(self,user_id=None):
        sql='''SELECT r.*,t.prompt,t.response FROM human_reviews r JOIN turns t ON t.id=r.turn_id'''
        with self.store.connect() as db:
            rows=db.execute(sql+(' WHERE r.user_id=?' if user_id else '')+' ORDER BY r.created DESC LIMIT 100',(user_id,) if user_id else ()).fetchall()
        return [dict(row) for row in rows]

    def resolve_review(self,identifier,resolution):
        if not resolution.strip():raise ValueError('Enter a review response')
        with self.store.connect() as db:
            return db.execute("UPDATE human_reviews SET status='closed',resolution=? WHERE id=?",(resolution,identifier)).rowcount>0
