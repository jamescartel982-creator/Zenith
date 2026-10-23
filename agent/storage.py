"""Transactional, conversation-scoped storage and explicit dataset approvals."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Store:
    def __init__(self, data_dir="data"):
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        self.path = Path(data_dir) / "zenith.sqlite3"
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS turns (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                prompt TEXT NOT NULL, response TEXT NOT NULL,
                messages TEXT NOT NULL, model TEXT NOT NULL,
                created_at TEXT NOT NULL, rating TEXT,
                approved INTEGER NOT NULL DEFAULT 0, correction TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS turns_session ON turns(session_id, created_at)")
            db.execute('''CREATE TABLE IF NOT EXISTS human_reviews (
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL, session_id TEXT NOT NULL, turn_id TEXT NOT NULL,
                reason TEXT NOT NULL, status TEXT NOT NULL, resolution TEXT NOT NULL, created REAL NOT NULL,
                UNIQUE(user_id, turn_id))''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(turns)')}
            for name in ('deliberation', 'sources', 'quality', 'performance'):
                if name not in columns:
                    db.execute(f'ALTER TABLE turns ADD COLUMN {name} TEXT')
            db.execute("""CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY, source_id TEXT NOT NULL, url TEXT NOT NULL,
                text TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(source_id, content_hash)
            )""")
            db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING
                fts5(text, content='knowledge', content_rowid='rowid')""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS knowledge_insert AFTER INSERT ON knowledge BEGIN
                INSERT INTO knowledge_fts(rowid, text) VALUES (new.rowid, new.text); END""")
            db.execute("""CREATE TRIGGER IF NOT EXISTS knowledge_delete AFTER DELETE ON knowledge BEGIN
                INSERT INTO knowledge_fts(knowledge_fts, rowid, text) VALUES ('delete', old.rowid, old.text); END""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, session_id, prompt, response, messages, model, deliberation=None, sources=None, quality=None, performance=None):
        turn_id = str(uuid4())
        with self.connect() as db:
            db.execute("""INSERT INTO turns
                (id, session_id, prompt, response, messages, model, created_at, deliberation, sources, quality, performance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                turn_id, session_id, prompt, response, json.dumps(messages), model,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(deliberation) if deliberation else None, json.dumps(sources) if sources else None,
                json.dumps(quality) if quality else None,json.dumps(performance) if performance else None))
        return turn_id

    def history(self, session_id, limit=12):
        with self.connect() as db:
            rows = db.execute("""SELECT id, prompt, response, rating, approved, correction, deliberation, sources, quality, performance
                FROM turns WHERE session_id=? ORDER BY rowid DESC LIMIT ?""",
                (session_id, limit)).fetchall()
        result = []
        for row in reversed(rows):
            item = dict(row)
            item['deliberation'] = json.loads(item['deliberation']) if item['deliberation'] else None
            item['sources'] = json.loads(item['sources']) if item['sources'] else []
            item['quality'] = json.loads(item['quality']) if item['quality'] else None
            item['performance'] = json.loads(item['performance']) if item['performance'] else None
            result.append(item)
        return result

    def review(self, session_id, turn_id, rating, approved=False, correction=None):
        from .admin import contains_admin_code
        if correction and contains_admin_code(correction):
            raise ValueError('Never save an owner code in a review or training example')
        if rating not in {"good", "bad"}:
            raise ValueError("rating must be good or bad")
        correction = correction.strip() if correction else None
        if approved and rating == "bad" and not correction:
            raise ValueError("A bad answer needs a corrected response before approval")
        with self.connect() as db:
            result = db.execute("""UPDATE turns SET rating=?, approved=?, correction=?
                WHERE id=? AND session_id=?""",
                (rating, int(approved), correction, turn_id, session_id))
        return result.rowcount == 1

    def approved_examples(self):
        with self.connect() as db:
            rows = db.execute("""SELECT * FROM turns WHERE approved=1
                AND (rating='good' OR (rating='bad' AND correction IS NOT NULL))
                ORDER BY rowid""").fetchall()
        result = []
        for row in rows:
            messages = json.loads(row["messages"])
            messages.append({"role": "assistant", "content": row["correction"] or row["response"]})
            result.append({"messages": messages, "prompt": row["prompt"], "source_id": row["id"], "conversation_id": row["session_id"]})
        return result

    def delete_session(self, session_id):
        with self.connect() as db:
            db.execute("DELETE FROM turns WHERE session_id=?", (session_id,))
            db.execute('DELETE FROM human_reviews WHERE session_id=?', (session_id,))
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='generation_metrics'").fetchone():
                db.execute('DELETE FROM generation_metrics WHERE session_id=?',(session_id,))


    def add_document(self, source_id, url, text):
        import hashlib
        from urllib.parse import urlparse
        text = text.strip()
        parsed = urlparse(url)
        if not text or len(text) > 12000 or not source_id or parsed.scheme != 'https' or not parsed.netloc:
            raise ValueError('Document needs a source, HTTPS URL and 1–12000 text characters')
        identifier = str(uuid4())
        with self.connect() as db:
            result = db.execute("""INSERT OR IGNORE INTO knowledge
                (id, source_id, url, text, content_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
                (identifier, source_id, url, text, hashlib.sha256(text.encode()).hexdigest(),
                 datetime.now(timezone.utc).isoformat()))
        return identifier if result.rowcount else None

    def knowledge_stats(self):
        with self.connect() as db:
            row = db.execute('SELECT COUNT(*) AS documents, COUNT(DISTINCT source_id) AS total_sources FROM knowledge').fetchone()
        return dict(row)

    def search_documents(self, query, limit=3):
        import re
        if not 0 <= limit <= 5:
            raise ValueError('Knowledge result limit must be 0–5')
        stopwords = set('what which where when how why who is are was were the an to that this and or for with as of on in at by from do does did please could would should can you me your our'.split())
        terms = [term for term in dict.fromkeys(re.findall(r'[^\W_]{2,}', query.casefold(), flags=re.UNICODE)) if term not in stopwords][:16]
        if not terms or limit == 0:
            return []
        # User input is tokenized and quoted, never interpreted as FTS syntax.
        expression = ' OR '.join('"' + term + '"' for term in terms)
        with self.connect() as db:
            rows = db.execute("""SELECT k.id, k.source_id, k.url, k.text
                FROM knowledge_fts JOIN knowledge AS k ON k.rowid=knowledge_fts.rowid
                WHERE knowledge_fts MATCH ? ORDER BY bm25(knowledge_fts) LIMIT ?""",
                (expression, limit)).fetchall()
        return [{'id': row['id'], 'source_id': row['source_id'], 'url': row['url'],
                 'excerpt': row['text'][:600]} for row in rows]

    def delete_source(self, source_id):
        with self.connect() as db:
            return db.execute('DELETE FROM knowledge WHERE source_id=?', (source_id,)).rowcount
