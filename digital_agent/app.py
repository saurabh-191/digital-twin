"""Responsive Gradio UI with bounded queueing and deployment settings."""
import logging
import os
import socket
import gradio as gr
from starlette.responses import JSONResponse
from starlette.routing import Route
from .config import ROOT, Settings, load_environment
from .agent import ChatError, DigitalAgent
from .styles import CSS, SUGGESTIONS, theme

async def healthz(request):
    return JSONResponse({'status': 'ok'})

def create_app(agent=None, settings=None):
    settings = settings or Settings.from_env()
    agent = agent or DigitalAgent(settings)

    def respond(message, history):
        try:
            return agent.chat(message, history)
        except ChatError as error:
            raise gr.Error(str(error)) from None
        except Exception:
            logging.getLogger(__name__).error('Unexpected chat error', exc_info=False)
            raise gr.Error('Something went wrong. Please try again.') from None

    with gr.Blocks(title='Digital Agent', analytics_enabled=False, fill_height=True) as demo:
        with gr.Row(elem_id='app-header'):
            gr.HTML('<p>Digital Agent <small> / CAREER & EXPERIENCE</small></p>', elem_id='brand')
            new_chat = gr.Button('? New chat', elem_id='new-chat', size='sm')
        with gr.Column(elem_id='chat-shell'):
            chatbot = gr.Chatbot(
                elem_id='conversation', height='55vh', min_height=320, show_label=False,
                layout='bubble', buttons=['copy'], feedback_options=[],
                allow_file_downloads=False, allow_tags=False, sanitize_html=True,
                placeholder='<h1>What would you like to know?</h1><p>Explore my background, skills, and work.<br>You?re chatting with an AI digital twin.</p>',
            )
            textbox = gr.Textbox(placeholder='Ask about my work or experience?',
                elem_id='composer', show_label=False, container=False, lines=1, max_lines=6,
                max_length=settings.max_input_chars, submit_btn="?", stop_btn="?")
            chat = gr.ChatInterface(
                respond, chatbot=chatbot, textbox=textbox, examples=SUGGESTIONS,
                cache_examples=False, run_examples_on_click=True, save_history=False,
                flagging_mode='never', analytics_enabled=False, autofocus=False,
                concurrency_limit=settings.concurrency, api_visibility='private',
                fill_height=True,
            )
            gr.Markdown('AI replies may be inaccurate. Chats are sent to the AI provider. '
                'Contact details you choose to share and unanswered questions are saved for follow-up. '
                'Please avoid sensitive information.', elem_id='privacy-note')
        # Clear all ChatInterface states together; do not leave previous context behind.
        new_chat.click(lambda: ([], [], [], '', None),
            outputs=[chat.chatbot, chat.chatbot_state, chat.chatbot_value, chat.textbox, chat.saved_input],
            queue=False, api_visibility='private')
    demo.queue(max_size=settings.queue_size, default_concurrency_limit=settings.concurrency)
    return demo

def select_port(host, preferred, attempts=100):
    """Skip occupied/reserved local ports without terminating other applications."""
    for port in range(preferred, min(preferred + attempts, 65536)):
        try:
            with socket.create_server((host, port)):
                return port
        except OSError:
            continue
    raise OSError(f'No available port between {preferred} and {min(preferred + attempts - 1, 65535)}. Set PORT to another range.')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    load_environment()
    settings = Settings.from_env()
    # Keep fixed-port deployments strict; local development can skip busy ports.
    strict_port = os.getenv('PORT_STRICT', '').lower() in ('1', 'true', 'yes')
    port = settings.port if strict_port else select_port(settings.host, settings.port)
    if port != settings.port:
        logging.getLogger(__name__).warning(
            'Port %s is unavailable; using port %s instead.', settings.port, port)
    demo = create_app(settings=settings)
    demo.launch(
        server_name=settings.host, server_port=port, inbrowser=False, share=False,
        show_error=False, auth=(settings.auth_user, settings.auth_password) if settings.auth_user else None,
        blocked_paths=[str(ROOT / '.env'), str(ROOT.parent / '.env'), str(ROOT / 'runtime'), str(settings.database), str(ROOT / 'data')],
        max_file_size='1mb', enable_monitoring=False, footer_links=[],
        root_path=os.getenv('ROOT_PATH', ''),
        theme=theme(), css=CSS,
        app_kwargs={'routes': [Route('/healthz', healthz)]},
    )

if __name__ == '__main__':
    main()
