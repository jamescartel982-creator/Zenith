"""Owner TOTP enrollment, encrypted secrets, and single-use verification."""
import base64
import hashlib
import hmac
import os
from pathlib import Path
import time
import pyotp
from cryptography.fernet import Fernet


def local_key(store,name='owner-mfa.key',create=True):
    path=store.path.parent/name
    if not create and not path.is_file():
        raise ValueError('MFA encryption key is missing; restore the original key or use local owner recovery')
    try:
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:
        for _ in range(50):
            value=path.read_bytes()
            if len(value)==44:return value
            time.sleep(0.02)
        raise ValueError('MFA encryption key is incomplete; local recovery is required')
    key=Fernet.generate_key()
    with os.fdopen(descriptor,'wb') as handle:handle.write(key)
    return key


class OwnerMFA:
    def __init__(self,store):
        self.store=store
        with store.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS owner_mfa (user_id TEXT PRIMARY KEY, secret TEXT NOT NULL, enabled INTEGER NOT NULL, expires REAL NOT NULL, last_step INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS owner_mfa_sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires REAL NOT NULL)')

    def enabled(self,user_id):
        with self.store.connect() as db:
            return db.execute('SELECT 1 FROM owner_mfa WHERE user_id=? AND enabled=1',(user_id,)).fetchone() is not None

    def verified(self,user_id,token):
        with self.store.connect() as db:
            return db.execute('''SELECT 1 FROM owner_mfa_sessions m JOIN login_sessions s ON s.token_hash=m.token_hash
                WHERE m.token_hash=? AND m.user_id=? AND s.user_id=m.user_id AND m.expires>? AND s.expires>?''',
                (hashlib.sha256(token.encode()).hexdigest(),user_id,time.time(),time.time())).fetchone() is not None

    def begin(self,user_id,username):
        secret=pyotp.random_base32()
        encrypted=Fernet(local_key(self.store)).encrypt(secret.encode()).decode()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT enabled FROM owner_mfa WHERE user_id=?',(user_id,)).fetchone()
            if row and row['enabled']:raise ValueError('MFA is already enabled; use local owner recovery to reset it')
            db.execute('INSERT OR REPLACE INTO owner_mfa VALUES (?,?,0,?,-1)',(user_id,encrypted,time.time()+600))
        return {'secret':secret,'provisioning_uri':pyotp.TOTP(secret).provisioning_uri(name=username,issuer_name='Zenith Owner'),
                'expires_in_seconds':600,'notice':'Store in your authenticator. This secret is shown only during setup; keep it out of chat.'}

    def verify(self,user_id,token,code,enroll=False):
        if not isinstance(code,str) or len(code)!=6 or not code.isascii() or not code.isdigit():return False
        with self.store.connect() as db:
            row=db.execute('SELECT * FROM owner_mfa WHERE user_id=?',(user_id,)).fetchone()
        if row is None or (not row['enabled'] and (not enroll or row['expires']<time.time())):return False
        from cryptography.fernet import InvalidToken
        try:secret=Fernet(local_key(self.store,create=False)).decrypt(row['secret'].encode()).decode()
        except (ValueError,OSError,InvalidToken):return False
        totp=pyotp.TOTP(secret);step=int(time.time()//30)
        matched=next((n for n in [step-1,step,step+1] if hmac.compare_digest(totp.at(n*30),code)),None)
        if matched is None:return False
        token_hash=hashlib.sha256(token.encode()).hexdigest()
        with self.store.connect() as db:
            session=db.execute('SELECT user_id,expires FROM login_sessions WHERE token_hash=? AND expires>?',(token_hash,time.time())).fetchone()
            if not session or session['user_id']!=user_id:return False
            # CAS prevents simultaneous requests from reusing a valid OTP.
            changed=db.execute('UPDATE owner_mfa SET enabled=1,last_step=? WHERE user_id=? AND last_step<?',(matched,user_id,matched)).rowcount
            if not changed:return False
            db.execute('INSERT OR REPLACE INTO owner_mfa_sessions VALUES (?,?,?)',(token_hash,user_id,min(session['expires'],time.time()+900)))
        return True


def contains_enrollment_secret(store,text):
    """Keep known enrollment secrets out of model prompts and saved memories."""
    from cryptography.fernet import InvalidToken
    with store.connect() as db:
        exists=db.execute("SELECT 1 FROM sqlite_master WHERE name='owner_mfa'").fetchone()
        rows=db.execute('SELECT secret FROM owner_mfa').fetchall() if exists else []
    if not rows:return False
    try:cipher=Fernet(local_key(store,create=False))
    except (ValueError,OSError):return False
    for row in rows:
        try:secret=cipher.decrypt(row['secret'].encode()).decode()
        except InvalidToken:continue
        if secret in text.upper():return True
    return False
