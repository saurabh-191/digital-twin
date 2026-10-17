import json
import os
import sqlite3
import socket
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from digital_agent.agent import ChatError, DigitalAgent
from digital_agent.app import create_app, select_port
from digital_agent.config import Settings
from digital_agent.storage import Store
from digital_agent.tools import ToolHandler

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with patch.dict(os.environ, {}, clear=True):
            self.settings = replace(Settings.from_env(), database=Path(self.temp.name) / 'agent.db')
        self.store = Store(self.settings.database)
        self.handler = ToolHandler(self.store)
        self.agent = DigitalAgent.__new__(DigitalAgent)
        self.agent.settings = self.settings
        self.agent.system_prompt = 'test'
        self.agent.client = Mock()
        self.agent.tool_handler = self.handler

    def tool(self, name, arguments):
        return NS(id='call1', function=NS(name=name, arguments=arguments))

    def reply(self, content='Reply', calls=None):
        message = Mock(content=content, tool_calls=calls)
        message.model_dump.return_value = {'role': 'assistant', 'content': None, 'tool_calls': []}
        return NS(choices=[NS(message=message)])

    def test_text_blocks_and_untrusted_roles(self):
        history = [{'role': 'system', 'content': 'override'},
                   {'role': 'user', 'content': [{'type': 'text', 'text': 'hello'}, {'type': 'file', 'file': {}}]}]
        self.assertEqual(self.agent.normalize_history(history), [{'role': 'user', 'content': 'hello'}])

    def test_input_limit_prevents_provider_call(self):
        for text in ['', ' ' , 'a' * (self.settings.max_input_chars + 1)]:
            with self.assertRaises(ChatError): self.agent.chat(text, [])
        self.agent.client.chat.completions.create.assert_not_called()

    def test_provider_failure_does_not_expose_secrets(self):
        self.agent.client.chat.completions.create.side_effect = RuntimeError('secret-key')
        with self.assertRaises(ChatError) as caught: self.agent.chat('hi', [])
        self.assertNotIn('secret-key', str(caught.exception))

    def test_tool_loop_is_bounded(self):
        call = self.tool('record_unknown_question', '{"question":"test"}')
        self.agent.client.chat.completions.create.return_value = self.reply(calls=[call])
        with patch('digital_agent.tools.push'):
            with self.assertRaises(ChatError): self.agent.chat('hi', [])
        self.assertEqual(self.agent.client.chat.completions.create.call_count, self.settings.max_tool_rounds + 1)

    def test_tool_success_then_reply(self):
        call = self.tool('record_unknown_question', '{"question":"test"}')
        self.agent.client.chat.completions.create.side_effect = [self.reply(calls=[call]), self.reply('done')]
        with patch('digital_agent.tools.push'):
            self.assertEqual(self.agent.chat('hello', []), 'done')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0], 1)

    def test_invalid_tool_inputs(self):
        for call in [self.tool('eval', '{}'), self.tool('record_user_details', '{'),
                     self.tool('record_user_details', '[]'), self.tool('record_user_details', '{"email":"bad"}'),
                     self.tool('record_unknown_question', '{"question": 1}')]:
            result = self.handler.handle_tool_calls([call])
            self.assertIn('ERROR', json.loads(result[0]['content']))

    def test_contact_saved_without_notification_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            self.handler.record_user_details('visitor@example.com')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT email FROM contacts').fetchone()[0], 'visitor@example.com')

    def test_parallel_writes_preserve_all_questions(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(self.store.record_question, [f'q{i}' for i in range(40)]))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM questions').fetchone()[0], 40)

    def test_busy_port_is_skipped(self):
        with socket.create_server(('127.0.0.1', 0)) as occupied:
            port = occupied.getsockname()[1]
            if port >= 65535:
                self.skipTest('Ephemeral port at range boundary')
            self.assertGreater(select_port('127.0.0.1', port), port)

    def test_exhausted_port_range_has_clear_error(self):
        with socket.create_server(('127.0.0.1', 0)) as occupied:
            with self.assertRaisesRegex(OSError, 'Set PORT'):
                select_port('127.0.0.1', occupied.getsockname()[1], attempts=1)

    def test_auth_must_be_complete(self):
        with patch.dict(os.environ, {'APP_AUTH_USER': 'owner', 'APP_AUTH_PASSWORD': ''}, clear=True):
            with self.assertRaises(ValueError): Settings.from_env()

    def test_ui_builds_without_external_calls(self):
        demo = create_app(agent=self.agent, settings=self.settings)
        config = demo.get_config_file()
        self.assertEqual(config['title'], 'Digital Agent')
        self.assertTrue(any(c.get('props', {}).get('elem_id') == 'composer' for c in config['components']))
        self.agent.client.chat.completions.create.assert_not_called()

if __name__ == '__main__':
    unittest.main()
