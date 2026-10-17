"""Validated runtime settings; deployment environment overrides dotenv files."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / 'data'

def load_environment():
    load_dotenv(ROOT / '.env', override=False)
    load_dotenv(ROOT.parent / '.env', override=False)

def positive_int(name, default):
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f'{name} must be a positive integer')
    return value

@dataclass(frozen=True)
class Settings:
    model: str
    timeout: int
    max_input_chars: int
    history_messages: int
    max_tool_rounds: int
    max_output_tokens: int
    concurrency: int
    queue_size: int
    host: str
    port: int
    database: Path
    auth_user: str
    auth_password: str

    @classmethod
    def from_env(cls):
        user, password = os.getenv('APP_AUTH_USER', ''), os.getenv('APP_AUTH_PASSWORD', '')
        if bool(user) != bool(password):
            raise ValueError('Set both APP_AUTH_USER and APP_AUTH_PASSWORD or neither')
        port = positive_int('PORT', 7860)
        if port > 65535:
            raise ValueError('PORT must be between 1 and 65535')
        return cls(
            model=os.getenv('OPEN_ROUTER_MODEL', 'nvidia/nemotron-3.5-lightning:free'),
            timeout=positive_int('API_TIMEOUT_SECONDS', 45),
            max_input_chars=positive_int('MAX_INPUT_CHARS', 4000),
            history_messages=positive_int('HISTORY_MESSAGES', 20),
            max_tool_rounds=positive_int('MAX_TOOL_ROUNDS', 4),
            max_output_tokens=positive_int('MAX_OUTPUT_TOKENS', 1200),
            concurrency=positive_int('CHAT_CONCURRENCY', 4),
            queue_size=positive_int('QUEUE_SIZE', 32),
            host=os.getenv('HOST', '127.0.0.1'), port=port,
            database=Path(os.getenv('DATABASE_PATH', str(ROOT / 'runtime' / 'agent.sqlite3'))).resolve(),
            auth_user=user, auth_password=password,
        )

def create_client(settings):
    from openai import OpenAI
    key = os.getenv('OPEN_ROUTER_KEY')
    if not key:
        raise ValueError('Set OPEN_ROUTER_KEY in digital-agent/.env or the environment')
    return OpenAI(api_key=key, base_url='https://openrouter.ai/api/v1',
                  timeout=settings.timeout, max_retries=1)
