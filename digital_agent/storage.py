"""Transactional local storage. Each write uses its own SQLite connection."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

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


def database_error_hint(error):
    """Classify errors using fixed messages; never echo server text or credentials."""
    state = getattr(error, 'sqlstate', None)
    message = str(error).lower()
    if isinstance(error, ImportError):
        return 'Postgres driver is missing. Install the requirements and rebuild the image.'
    if state in ('28P01', '28000') or 'password authentication failed' in message:
        return 'Authentication failed. Copy a fresh connection string from Neon Connect.'
    if state == '3D000':
        return 'The selected database does not exist. Check the database selected in Neon Connect.'
    if state == '42501' or 'permission denied' in message:
        return 'The database role lacks permissions. It needs permission to create and write tables in its schema.'
    if 'unsupported startup parameter' in message:
        return 'The pooler rejected a startup option. Use the latest app code and the unmodified Neon URL.'
    if 'ssl' in message or 'certificate' in message or 'channel binding' in message:
        return 'TLS connection failed. Copy the full Neon URL, including its SSL parameters.'
    if 'translate host name' in message or 'name or service not known' in message or 'getaddrinfo' in message:
        return 'Database hostname could not be resolved. Verify the host using Neon Connect.'
    if 'timeout' in message or 'timed out' in message:
        return 'Database connection timed out. Check Neon project status and network access, then retry.'
    if 'connection refused' in message or 'network is unreachable' in message:
        return 'Database server could not be reached. Check project status, host, port, and access restrictions.'
    if isinstance(error, ValueError) or 'invalid conninfo' in message or 'invalid connection option' in message:
        return 'Invalid DATABASE_URL. Paste only the postgresql:// URL, without psql, quotes, or DATABASE_URL=.'
    return 'Check DATABASE_URL, Neon project status, and the database role permissions.'


class PostgresStore:
    """Durable storage on an external Postgres service; never falls back silently."""
    def __init__(self, url):
        self.url = url
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname or not parsed.path.strip('/'):
                raise ValueError('Invalid database URL')
            with self.connect() as db:
                db.execute('CREATE TABLE IF NOT EXISTS questions (id BIGSERIAL PRIMARY KEY, question TEXT NOT NULL, created_at TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS contacts (id BIGSERIAL PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL)')
        except Exception as error:
            raise RuntimeError('Postgres initialization failed. ' + database_error_hint(error)) from None

    @contextmanager
    def connect(self):
        import psycopg
        # SET LOCAL is scoped to this transaction and works with transaction poolers.
        with psycopg.connect(self.url, connect_timeout=30) as connection:
            connection.execute("SET LOCAL statement_timeout = '10s'")
            yield connection

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
