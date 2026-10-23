"""OS-owner bootstrap and short-lived, account-bound administrator elevation."""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from .paths import zenith_home

CODE_PATTERN = re.compile(r'zenith-admin-[A-Za-z0-9_-]{43}')


def contains_admin_code(text):
    return bool(CODE_PATTERN.search(text))


class AdminStore:
    def __init__(self, store):
        self.store = store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS admin_owner (singleton INTEGER PRIMARY KEY CHECK(singleton=1), user_id TEXT NOT NULL, salt TEXT NOT NULL, code_hash TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS admin_elevations (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL, devil INTEGER NOT NULL DEFAULT 0)')
            db.execute('CREATE TABLE IF NOT EXISTS admin_audit (created REAL NOT NULL, user_id TEXT NOT NULL, event TEXT NOT NULL)')

    @staticmethod
    def digest(code, salt):
        return hashlib.pbkdf2_hmac('sha256', code.encode(), bytes.fromhex(salt), 600000).hex()

    def initialize(self, username, path=None, rotate=False):
        path = Path(path or zenith_home() / 'admin-code.txt').expanduser().resolve()
        with self.store.connect() as db:
            user = db.execute('SELECT id FROM users WHERE username=?', (username.strip().casefold(),)).fetchone()
            owner = db.execute('SELECT user_id FROM admin_owner WHERE singleton=1').fetchone()
        if not user:
            raise ValueError('Create your local account in the browser first, then use its exact username')
        if (owner or path.exists()) and not rotate:
            raise ValueError('Owner setup already exists. Use --rotate deliberately to replace the code and revoke elevations')
        code = 'zenith-admin-' + secrets.token_urlsafe(32)
        salt = secrets.token_hex(16)
        hashed = self.digest(code, salt)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix='.zenith-admin-', dir=path.parent)
            temporary = Path(temporary_name)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                handle.write(code + '\n')
            # File replacement precedes DB rotation; the existing DB is not changed
            # if this protected local file cannot be written.
            os.replace(temporary, path)
            with self.store.connect() as db:
                db.execute('INSERT OR REPLACE INTO admin_owner VALUES (1, ?, ?, ?)', (user['id'], salt, hashed))
                db.execute('DELETE FROM admin_elevations')
                db.execute("DELETE FROM skill_activations WHERE token_hash<>''")
                db.execute('INSERT INTO admin_audit VALUES (?, ?, ?)', (time.time(), user['id'], 'owner-code-rotated' if owner else 'owner-configured'))
        finally:
            if temporary is not None: temporary.unlink(missing_ok=True)
        return path

    def status(self, user_id, token):
        digest = hashlib.sha256(token.encode()).hexdigest()
        now = time.time()
        with self.store.connect() as db:
            owner = db.execute('SELECT user_id FROM admin_owner WHERE singleton=1').fetchone()
            row = db.execute('''SELECT e.expires, e.devil FROM admin_elevations e
                JOIN login_sessions s ON s.token_hash=e.token_hash AND s.user_id=e.user_id
                WHERE e.token_hash=? AND e.user_id=? AND e.expires>? AND s.expires>?''', (digest, user_id, now, now)).fetchone()
        return {'eligible': bool(owner and owner['user_id']==user_id), 'elevated': row is not None,
                'devil_mode': bool(row and row['devil']), 'expires_at': row['expires'] if row else None}

    def unlock(self, user_id, token, code):
        if not CODE_PATTERN.fullmatch(code): return False
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.store.connect() as db:
            owner = db.execute('SELECT * FROM admin_owner WHERE singleton=1').fetchone()
            session = db.execute('SELECT user_id FROM login_sessions WHERE token_hash=? AND expires>?', (digest,time.time())).fetchone()
        if not owner or owner['user_id']!=user_id or not session or session['user_id']!=user_id:
            return False
        valid = hmac.compare_digest(owner['code_hash'], self.digest(code,owner['salt']))
        with self.store.connect() as db:
            db.execute('INSERT INTO admin_audit VALUES (?, ?, ?)', (time.time(), user_id, 'unlock-ok' if valid else 'unlock-denied'))
            if valid:
                db.execute('DELETE FROM skill_activations WHERE token_hash=?', (digest,))
                db.execute('DELETE FROM admin_elevations WHERE expires<=?', (time.time(),))
                db.execute('INSERT OR REPLACE INTO admin_elevations VALUES (?, ?, ?, 0)', (digest,user_id,time.time()+900))
        return valid

    def mode(self, user_id, token, enabled):
        if not self.status(user_id,token)['elevated']: raise PermissionError('Administrator elevation required')
        with self.store.connect() as db:
            db.execute('UPDATE admin_elevations SET devil=? WHERE token_hash=? AND user_id=?', (int(enabled),hashlib.sha256(token.encode()).hexdigest(),user_id))
            db.execute('INSERT INTO admin_audit VALUES (?, ?, ?)', (time.time(), user_id, 'devil-on' if enabled else 'devil-off'))
        return self.status(user_id,token)

    def record_tool(self, user_id, tool):
        with self.store.connect() as db:
            db.execute('INSERT INTO admin_audit VALUES (?, ?, ?)', (time.time(),user_id,'tool:'+tool))

    def lock(self, token):
        with self.store.connect() as db:
            db.execute('DELETE FROM admin_elevations WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
            db.execute('DELETE FROM skill_activations WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init'])
    parser.add_argument('--username', required=True, help='Exact existing local account username')
    parser.add_argument('--rotate', action='store_true', help='Replace the existing code and revoke all elevations')
    args = parser.parse_args()
    from .config import Settings
    from .storage import Store
    from .personal import PersonalStore
    store = Store(Settings().data_dir); PersonalStore(store)
    try: path = AdminStore(store).initialize(args.username,rotate=args.rotate)
    except (ValueError,OSError) as exc: parser.error(str(exc))
    print('Owner configured. Your secret code is in this protected LOCAL file: ' + str(path))
    print('Read it privately on your own machine. Never commit it, share it, or paste it into normal chat.')
    print('Sign in as your account, open Admin, then unlock. Elevation lasts 15 minutes.')


if __name__=='__main__': main()
