"""Bounded conversation loop with normalized, text-only visitor history."""
import logging
from .config import Settings, create_client
from .profile import build_system_prompt
from .storage import create_store
from .tools import ToolHandler, tools

logger = logging.getLogger(__name__)

class ChatError(Exception):
    """Safe, visitor-facing failure message."""

class DigitalAgent:
    def __init__(self, settings=None):
        self.settings = settings or Settings.from_env()
        self.client = create_client(self.settings)
        self.system_prompt = build_system_prompt()
        self.tool_handler = ToolHandler(create_store(self.settings.database))

    def normalize_history(self, history):
        normalized = []
        for item in list(history or [])[-self.settings.history_messages:]:
            if not isinstance(item, dict) or item.get('role') not in ('user', 'assistant'):
                continue
            content = item.get('content', '')
            if isinstance(content, list):
                content = '\n'.join(block['text'] for block in content
                    if isinstance(block, dict) and block.get('type') == 'text' and isinstance(block.get('text'), str))
            if isinstance(content, str) and content.strip():
                normalized.append({'role': item['role'], 'content': content[:self.settings.max_input_chars]})
        # Avoid starting with a previous assistant reply after trimming history.
        while normalized and normalized[0]['role'] != 'user':
            normalized.pop(0)
        return normalized

    def chat(self, message, history):
        if not isinstance(message, str) or not message.strip():
            raise ChatError('Please enter a question to get started.')
        if len(message) > self.settings.max_input_chars:
            raise ChatError(f'Please keep your message under {self.settings.max_input_chars:,} characters.')
        messages = [{'role': 'system', 'content': self.system_prompt}]
        messages.extend(self.normalize_history(history))
        messages.append({'role': 'user', 'content': message.strip()})
        try:
            for round_index in range(self.settings.max_tool_rounds + 1):
                response = self.client.chat.completions.create(
                    model=self.settings.model, messages=messages, tools=tools,
                    max_tokens=self.settings.max_output_tokens)
                choice = response.choices[0]
                if choice.message.tool_calls:
                    if round_index == self.settings.max_tool_rounds or len(choice.message.tool_calls) > 8:
                        raise ChatError('This request needed too many steps. Please try a simpler question.')
                    messages.append(choice.message.model_dump(exclude_none=True))
                    messages.extend(self.tool_handler.handle_tool_calls(choice.message.tool_calls))
                    continue
                if not choice.message.content:
                    raise ChatError('I could not generate a reply. Please try again.')
                return choice.message.content
        except ChatError:
            raise
        except Exception:
            # Do not include prompts, credentials, or provider responses in logs/UI.
            logger.error('Chat provider request failed', exc_info=False)
            raise ChatError('The assistant is temporarily unavailable. Please try again shortly.') from None
