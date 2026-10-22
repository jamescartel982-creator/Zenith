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

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def add(self, session_id, prompt, response, messages, model):
        turn_id = str(uuid4())
        with self.connect() as db:
            db.execute("""INSERT INTO turns
                (id, session_id, prompt, response, messages, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                turn_id, session_id, prompt, response, json.dumps(messages), model,
                datetime.now(timezone.utc).isoformat()))
        return turn_id

    def history(self, session_id, limit=12):
        with self.connect() as db:
            rows = db.execute("""SELECT id, prompt, response, rating, approved, correction
                FROM turns WHERE session_id=? ORDER BY rowid DESC LIMIT ?""",
                (session_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def review(self, session_id, turn_id, rating, approved=False, correction=None):
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
            result.append({"messages": messages, "source_id": row["id"], "conversation_id": row["session_id"]})
        return result

    def delete_session(self, session_id):
        with self.connect() as db:
            db.execute("DELETE FROM turns WHERE session_id=?", (session_id,))
