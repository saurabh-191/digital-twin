import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from digital_agent.storage import Store, PostgresStore, create_store
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
