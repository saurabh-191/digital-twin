"""Allowlisted, validated model tools; contacts are saved before notification."""
import json
import logging
import re
from .notifications import push

logger = logging.getLogger(__name__)

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {"type": "string", "description": "Any additional info about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"},
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class ToolHandler:
    def __init__(self, store):
        self.store = store
        self.registry = {'record_user_details': self.record_user_details,
                         'record_unknown_question': self.record_unknown_question}

    @staticmethod
    def text(value, limit):
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError('Invalid tool input')
        return value.strip()

    def record_user_details(self, email, name='Name not provided', notes='not provided'):
        email = self.text(email, 254)
        name, notes = self.text(name, 200), self.text(notes, 2000)
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Invalid email address')
        self.store.record_contact(email, name, notes)
        push(f'Contact request from {name}: {email}. Notes: {notes}')
        return 'Contact request saved successfully'

    def record_unknown_question(self, question):
        question = self.text(question, 4000)
        self.store.record_question(question)
        push(f'Unanswered question: {question}')
        return 'Question saved successfully'

    def handle_tool_calls(self, calls):
        results = []
        for call in calls:
            try:
                tool = self.registry.get(call.function.name)
                if tool is None:
                    raise ValueError('Unknown tool')
                if len(call.function.arguments) > 10000:
                    raise ValueError('Tool input too large')
                arguments = json.loads(call.function.arguments)
                if not isinstance(arguments, dict):
                    raise ValueError('Expected tool arguments object')
                result = tool(**arguments)
            except (ValueError, TypeError):
                result = 'ERROR: Invalid tool arguments. Ask the visitor to correct the information.'
            except Exception:
                logger.error('Tool execution failed', exc_info=False)
                result = 'ERROR: Could not save the information. Do not claim success.'
            results.append({'role': 'tool', 'content': json.dumps(result), 'tool_call_id': call.id})
        return results
