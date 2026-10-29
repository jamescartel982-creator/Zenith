"""Conversation skill selection and live, account-bound authorization."""
import hashlib

from .skills import get_skill, list_skills


class SkillAccessDenied(PermissionError):
    pass


class ConversationAccessDenied(LookupError):
    pass


def parse_skill_command(text):
    parts = text.strip().split()
    if not parts or parts[0].casefold() not in {'/skill', '/skills'}:
        return None
    if len(text) > 200 or '\n' in text or '\r' in text or len(parts) > 2:
        raise ValueError('Use /skill list, /skill ID, /skill off, or /skill status')
    if parts[0].casefold() == '/skills':
        if len(parts) != 1:
            raise ValueError('Use /skills to list available skills')
        return 'list', None
    target = parts[1].casefold() if len(parts) == 2 else 'status'
    if target in {'list', 'status'}:
        return target, None
    return 'activate', 'general' if target == 'off' else target


class SkillAccess:
    def __init__(self, store, personal, admin):
        self.store, self.personal, self.admin = store, personal, admin
        from .skill_catalog import SkillCatalog
        self.catalog=SkillCatalog(store)

    def lookup(self, identifier):
        try:return get_skill(identifier)
        except ValueError:return self.catalog.get(identifier)

    def is_admin(self, user_id, token):
        if not user_id or not isinstance(token, str) or not 1 <= len(token) <= 128:
            return False
        state = self.admin.status(user_id, token)
        return state['eligible'] and state['elevated']

    def require(self, identifier, user_id=None, token=None):
        profile = self.lookup(identifier)
        if profile['access'] == 'admin' and not self.is_admin(user_id, token):
            raise SkillAccessDenied('Security skills require your owner login and a current admin-code unlock')
        return profile

    def _conversation(self, session_id, user_id, create=False):
        if not self.personal.conversation_access(session_id, user_id or '', create):
            raise ConversationAccessDenied('Conversation not found')

    def _selection(self, session_id):
        with self.store.connect() as db:
            return db.execute('SELECT skill, token_hash FROM skill_activations WHERE session_id=?', (session_id,)).fetchone()

    def active(self, session_id, user_id=None, token=None):
        row = self._selection(session_id)
        if row is None:
            return 'general'
        self._conversation(session_id, user_id)
        try:
            profile = self.lookup(row['skill'])
        except ValueError:
            profile = None
        if profile and profile['access'] == 'public':
            return profile['id']
        digest = hashlib.sha256((token or '').encode()).hexdigest()
        if profile and row['token_hash'] == digest and self.is_admin(user_id, token):
            return profile['id']
        # An expired, locked, rotated, or different login cannot inherit an
        # old protected activation, even if it later unlocks the same account.
        with self.store.connect() as db:
            db.execute('DELETE FROM skill_activations WHERE session_id=? AND skill=? AND token_hash=?',
                       (session_id, row['skill'], row['token_hash']))
        return 'general'

    def select(self, session_id, identifier, user_id=None, token=None):
        profile = self.require(identifier, user_id, token)
        self._conversation(session_id, user_id, create=True)
        digest = hashlib.sha256(token.encode()).hexdigest() if profile['access'] == 'admin' else ''
        with self.store.connect() as db:
            db.execute('INSERT OR REPLACE INTO skill_activations VALUES (?, ?, ?)', (session_id, identifier, digest))
        return {'type': 'skill-activation', 'skill': identifier, 'name': profile['name'],
                'message': 'Active skill: ' + profile['name']}

    def command(self, session_id, text, user_id=None, token=None):
        parsed = parse_skill_command(text)
        if parsed is None:
            raise ValueError('Expected /skill or /skills command')
        action, target = parsed
        if action == 'activate':
            return self.select(session_id, target, user_id, token)
        self._conversation(session_id, user_id)
        active = self.active(session_id, user_id, token)
        if action == 'status':
            return {'type': 'skill-status', 'skill': active, 'message': 'Active skill: ' + self.lookup(active)['name']}
        rows = list_skills(include_admin=self.is_admin(user_id, token))
        return {'type': 'skill-list', 'skill': active,
                'extended_catalog': self.catalog.status(self.is_admin(user_id, token)),
                'skills': [{'id': row['id'], 'name': row['name']} for row in rows],
                'message': 'Use /skill ID to activate a skill. Security skills appear after owner unlock.'}
