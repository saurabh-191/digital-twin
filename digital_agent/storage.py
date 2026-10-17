"""Transactional local storage. Each write uses its own SQLite connection."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, question TEXT NOT NULL, created_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def record_question(self, question):
        with self.connect() as db:
            db.execute('INSERT INTO questions (question, created_at) VALUES (?, ?)',
                       (question, datetime.now(timezone.utc).isoformat()))

    def record_contact(self, email, name, notes):
        with self.connect() as db:
            db.execute('INSERT INTO contacts (email, name, notes, created_at) VALUES (?, ?, ?, ?)',
                       (email, name, notes, datetime.now(timezone.utc).isoformat()))
