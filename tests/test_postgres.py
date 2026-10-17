"""Runs against a disposable Postgres service in CI; skipped locally without its URL."""
import os
import unittest
from uuid import uuid4
from digital_agent.storage import PostgresStore

@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Set TEST_DATABASE_URL for Postgres integration tests')
class PostgresIntegrationTests(unittest.TestCase):
    def test_records_persist_and_failed_transaction_rolls_back(self):
        store = PostgresStore(os.environ['TEST_DATABASE_URL'])
        prefix = 'ci-' + uuid4().hex
        email = prefix + '@example.com'
        try:
            store.record_question(prefix)
            store.record_contact(email, 'Test visitor', 'CI integration')
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT question FROM questions WHERE question=%s', (prefix,)).fetchone()[0], prefix)
                self.assertEqual(db.execute('SELECT name FROM contacts WHERE email=%s', (email,)).fetchone()[0], 'Test visitor')
            with self.assertRaises(ValueError):
                with store.connect() as db:
                    db.execute('INSERT INTO questions (question, created_at) VALUES (%s, %s)', (prefix + '-rollback', 'test'))
                    raise ValueError('Rollback test')
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM questions WHERE question=%s', (prefix + '-rollback',)).fetchone()[0], 0)
        finally:
            with store.connect() as db:
                db.execute('DELETE FROM questions WHERE question IN (%s, %s)', (prefix, prefix + '-rollback'))
                db.execute('DELETE FROM contacts WHERE email=%s', (email,))
