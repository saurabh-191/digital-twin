import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from digital_agent.storage import Store, PostgresStore, create_store, database_error_hint
from scripts.deploy_render import deployment_url

class DeploymentTests(unittest.TestCase):
    def test_deploy_hook_uses_exact_tested_commit(self):
        commit = 'a' * 40
        url = deployment_url('https://api.render.com/deploy/srv-test?key=fake&ref=old', commit)
        self.assertEqual(parse_qs(urlsplit(url).query), {'key': ['fake'], 'ref': [commit]})

    def test_hook_rejects_other_destinations_and_invalid_sha(self):
        for hook, commit in [('http://api.render.com/deploy/a', 'a' * 40),
                             ('https://other.example/deploy/a', 'a' * 40),
                             ('https://api.render.com/deploy/a', 'main')]:
            with self.assertRaises(ValueError): deployment_url(hook, commit)

    def test_local_storage_is_default(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'DATABASE_URL': ''}):
                self.assertIsInstance(create_store(Path(directory) / 'test.db'), Store)

    def test_postgres_selected_when_configured(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test-only'}):
            with patch('digital_agent.storage.PostgresStore') as store:
                self.assertIs(create_store(Path('unused')), store.return_value)
                store.assert_called_once_with('postgresql://test-only')

    def test_database_startup_error_does_not_expose_connection_details(self):
        with patch.object(PostgresStore, 'connect', side_effect=RuntimeError('private-password')):
            with self.assertRaises(RuntimeError) as caught: PostgresStore('private-url')
        self.assertNotIn('private-password', str(caught.exception))
        self.assertNotIn('private-url', str(caught.exception))


class PostgresConnectionTests(unittest.TestCase):
    def test_pooler_connection_uses_transaction_timeout_not_startup_options(self):
        store = PostgresStore.__new__(PostgresStore)
        store.url = 'postgresql://test:fake@localhost/test'
        with patch('psycopg.connect') as connect:
            connection = connect.return_value.__enter__.return_value
            with store.connect() as db:
                self.assertIs(db, connection)
                db.execute('SELECT 1')
            connect.assert_called_once_with(store.url, connect_timeout=30)
            self.assertEqual(connection.execute.call_args_list[0].args, ("SET LOCAL statement_timeout = '10s'",))
            connect.return_value.__exit__.assert_called_once()

    def test_authentication_hint_does_not_leak_raw_message(self):
        error = RuntimeError('password authentication failed for private-user secret-password')
        hint = database_error_hint(error)
        self.assertIn('Authentication failed', hint)
        self.assertNotIn('private-user', hint)
        self.assertNotIn('secret-password', hint)

    def test_permission_hint_uses_sqlstate(self):
        error = RuntimeError('private-details')
        error.sqlstate = '42501'
        self.assertIn('permissions', database_error_hint(error))

    def test_shell_command_is_rejected_without_connecting(self):
        with patch('psycopg.connect') as connect:
            with self.assertRaisesRegex(RuntimeError, 'Invalid DATABASE_URL'):
                PostgresStore("psql 'postgresql://user:secret@host/db'")
            connect.assert_not_called()
