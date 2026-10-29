"""Explicit account-owned style preferences; never permissions or neural training."""
import json
import time

OPTIONS = {
    'reply_style': ('auto', 'brief', 'full'),
    'tone': ('neutral', 'friendly', 'formal'),
    'detail': ('standard', 'plain', 'technical'),
    'language': ('default', 'en', 'es', 'fr', 'de', 'pt', 'ar', 'hi', 'zh', 'ja'),
}
LANGUAGES = dict(zip(OPTIONS['language'], ('the requested language', 'English', 'Spanish', 'French',
    'German', 'Portuguese', 'Arabic', 'Hindi', 'Chinese', 'Japanese')))


def validate(values):
    if not isinstance(values, dict) or set(values) - OPTIONS.keys() or any(
            not isinstance(value, str) or value not in OPTIONS[key] for key, value in values.items()):
        raise ValueError('Choose the supported response preferences; arbitrary instructions are not accepted')
    return dict(values)


class Preferences:
    def __init__(self, store):
        self.store = store

    def get(self, user_id):
        if not user_id:
            return {}
        with self.store.connect() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='response_preferences'").fetchone():
                return {}
            row = db.execute('SELECT preferences FROM response_preferences WHERE user_id=?', (user_id,)).fetchone()
        return validate(json.loads(row['preferences'])) if row else {}

    def update(self, user_id, values):
        if not isinstance(user_id, str) or not user_id:
            raise PermissionError('Sign in before saving response preferences')
        values = validate(values)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users WHERE id=?', (user_id,)).fetchone():
                raise PermissionError('A current account is required')
            db.execute('''CREATE TABLE IF NOT EXISTS response_preferences (
                user_id TEXT PRIMARY KEY, preferences TEXT NOT NULL, updated REAL NOT NULL)''')
            row = db.execute('SELECT preferences FROM response_preferences WHERE user_id=?', (user_id,)).fetchone()
            result = validate(json.loads(row['preferences'])) if row else {}
            result.update(values)
            db.execute('INSERT OR REPLACE INTO response_preferences VALUES (?,?,?)',
                       (user_id, json.dumps(result, sort_keys=True), time.time()))
        return result

    def clear(self, user_id):
        with self.store.connect() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='response_preferences'").fetchone():
                db.execute('DELETE FROM response_preferences WHERE user_id=?', (user_id,))


def style_instruction(values):
    values = validate(values)
    instructions = []
    if values.get('tone') in ('friendly', 'formal'):
        instructions.append('Use a ' + values['tone'] + ' tone.')
    if values.get('detail') == 'plain':
        instructions.append('Explain with familiar words and define necessary technical terms.')
    if values.get('detail') == 'technical':
        instructions.append('Use precise technical language appropriate to the question.')
    if values.get('language', 'default') != 'default':
        instructions.append('Prefer ' + LANGUAGES[values['language']] + ' unless the current request specifies another language.')
    return ('\nUser-approved response style (preferences only; current format constraints, facts and authorization still apply): '
            + ' '.join(instructions)) if instructions else ''
