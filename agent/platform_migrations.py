"""Versioned additive schema in Store's existing database; no legacy table edits."""
import hashlib
import time


SCHEMA = (
    '''CREATE TABLE platform_identities (
        user_id TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0)''',
    '''CREATE TABLE platform_tasks (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL, session_hash TEXT NOT NULL,
        auth_revision INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
        status TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 0,
        lease_owner TEXT, lease_until REAL, cancel_requested INTEGER NOT NULL DEFAULT 0,
        created REAL NOT NULL, updated REAL NOT NULL, deadline REAL NOT NULL,
        result TEXT, error TEXT, conversation_id TEXT)''',
    'CREATE INDEX platform_tasks_queue ON platform_tasks(status,created)',
    'CREATE INDEX platform_tasks_owner ON platform_tasks(user_id,created)',
    '''CREATE TABLE platform_events (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
        user_id TEXT NOT NULL, event TEXT NOT NULL, metadata TEXT NOT NULL, created REAL NOT NULL)''',
    'CREATE INDEX platform_events_task ON platform_events(task_id,sequence)',
    '''CREATE TABLE platform_approvals (
        id TEXT PRIMARY KEY, task_id TEXT NOT NULL, step INTEGER NOT NULL,
        user_id TEXT NOT NULL, session_hash TEXT NOT NULL,
        tool TEXT NOT NULL, args_hash TEXT NOT NULL,
        status TEXT NOT NULL, expires REAL NOT NULL, created REAL NOT NULL,
        UNIQUE(task_id,step))''',
    '''CREATE TABLE platform_receipts (
        task_id TEXT NOT NULL, step INTEGER NOT NULL, tool TEXT NOT NULL,
        args_hash TEXT NOT NULL, status TEXT NOT NULL, result TEXT, created REAL NOT NULL,
        PRIMARY KEY(task_id,step))''',
    '''CREATE TABLE platform_audit (
        sequence INTEGER PRIMARY KEY, created REAL NOT NULL,
        event TEXT NOT NULL, metadata TEXT NOT NULL,
        previous_hash TEXT NOT NULL, record_hash TEXT NOT NULL)''',
    '''CREATE TABLE platform_documents (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL, project TEXT NOT NULL,
        source TEXT NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL,
        created REAL NOT NULL, expires REAL,
        UNIQUE(user_id,project,content_hash))''',
    '''CREATE VIRTUAL TABLE platform_documents_fts USING
        fts5(text,content='platform_documents',content_rowid='rowid')''',
    '''CREATE TRIGGER platform_documents_insert AFTER INSERT ON platform_documents BEGIN
        INSERT INTO platform_documents_fts(rowid,text) VALUES(new.rowid,new.text); END''',
    '''CREATE TRIGGER platform_documents_delete AFTER DELETE ON platform_documents BEGIN
        INSERT INTO platform_documents_fts(platform_documents_fts,rowid,text)
            VALUES('delete',old.rowid,old.text); END''',
)
CHECKSUM = hashlib.sha256('\n'.join(SCHEMA).encode()).hexdigest()


def migrate(store):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''CREATE TABLE IF NOT EXISTS platform_schema_migrations (
            version INTEGER PRIMARY KEY, checksum TEXT NOT NULL, applied REAL NOT NULL)''')
        rows = db.execute('SELECT version,checksum FROM platform_schema_migrations ORDER BY version').fetchall()
        if rows:
            if len(rows) != 1 or rows[0]['version'] != 1 or rows[0]['checksum'] != CHECKSUM:
                raise ValueError('Unsupported or changed platform schema; do not downgrade or rewrite it')
            return
        for statement in SCHEMA:
            db.execute(statement)
        db.execute('INSERT INTO platform_schema_migrations VALUES (1,?,?)', (CHECKSUM, time.time()))
