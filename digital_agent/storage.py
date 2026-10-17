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


class PostgresStore:
    """Durable storage on an external Postgres service; never falls back silently."""
    def __init__(self, url):
        self.url = url
        try:
            with self.connect() as db:
                db.execute('CREATE TABLE IF NOT EXISTS questions (id BIGSERIAL PRIMARY KEY, question TEXT NOT NULL, created_at TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS contacts (id BIGSERIAL PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL)')
        except Exception:
            raise RuntimeError('Postgres initialization failed. Check DATABASE_URL and database access.') from None

    def connect(self):
        import psycopg
        return psycopg.connect(self.url, connect_timeout=15, options='-c statement_timeout=10000')

    def record_question(self, question):
        with self.connect() as db:
            db.execute('INSERT INTO questions (question, created_at) VALUES (%s, %s)',
                       (question, datetime.now(timezone.utc).isoformat()))

    def record_contact(self, email, name, notes):
        with self.connect() as db:
            db.execute('INSERT INTO contacts (email, name, notes, created_at) VALUES (%s, %s, %s, %s)',
                       (email, name, notes, datetime.now(timezone.utc).isoformat()))


def create_store(path):
    import os
    url = os.getenv('DATABASE_URL', '').strip()
    return PostgresStore(url) if url else Store(path)
