"""Server-derived actors; every use revalidates the session and live authority."""
from dataclasses import dataclass, field
import hashlib
import time


@dataclass(frozen=True)
class ActorContext:
    user_id: str
    session_hash: str = field(repr=False)
    revision: int


class Permissions:
    def __init__(self, store, personal, execution, config):
        self.store, self.personal, self.execution, self.config = store, personal, execution, config

    def resolve(self, token):
        user = self.personal.user_for_token(token)
        if user is None:
            raise PermissionError('A current account session is required')
        with self.store.connect() as db:
            db.execute('INSERT OR IGNORE INTO platform_identities(user_id) VALUES (?)', (user['id'],))
            revision = db.execute('SELECT revision FROM platform_identities WHERE user_id=?', (user['id'],)).fetchone()[0]
        actor = ActorContext(user['id'], hashlib.sha256(token.encode()).hexdigest(), revision)
        self.validate(actor)
        return actor

    def validate(self, actor, db=None):
        if not isinstance(actor, ActorContext):
            raise PermissionError('Untrusted actor')
        def check(connection):
            row = connection.execute('''SELECT i.revision FROM platform_identities i
                JOIN login_sessions s ON s.user_id=i.user_id
                WHERE i.user_id=? AND s.token_hash=? AND s.expires>?''',
                (actor.user_id, actor.session_hash, time.time())).fetchone()
            if row is None or row['revision'] != actor.revision:
                raise PermissionError('Session expired or platform authority was revoked')
        if db is not None:
            check(db)
        else:
            with self.store.connect() as connection:
                check(connection)

    def require_owner(self, actor):
        self.validate(actor)
        with self.store.connect() as db:
            now = time.time()
            row = db.execute('''SELECT 1 FROM admin_owner o
                JOIN admin_elevations e ON e.user_id=o.user_id
                JOIN owner_mfa m ON m.user_id=o.user_id AND m.enabled=1
                JOIN owner_mfa_sessions v ON v.user_id=o.user_id AND v.token_hash=e.token_hash
                WHERE o.user_id=? AND e.token_hash=? AND e.expires>? AND v.expires>?''',
                (actor.user_id, actor.session_hash, now, now)).fetchone()
        if row is None:
            raise PermissionError('Current owner elevation and verified MFA required')

    def require_tool(self, actor, capability):
        self.validate(actor)
        if not self.config.tools_enabled:
            raise PermissionError('Platform tools are disabled')
        return self.execution.require_session(actor.user_id, actor.session_hash, capability)

    def revoke(self, actor):
        self.validate(actor)
        with self.store.connect() as db:
            db.execute('UPDATE platform_identities SET revision=revision+1 WHERE user_id=?', (actor.user_id,))
