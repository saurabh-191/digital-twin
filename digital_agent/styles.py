"""Local theme and responsive ChatGPT-inspired styling."""
import gradio as gr

SUGGESTIONS = [
    'Tell me about your professional background.',
    'What are your strongest technical skills?',
    'Which projects best demonstrate your experience?',
    'How can I get in touch about an opportunity?',
]

def theme():
    return gr.themes.Monochrome(font=['ui-sans-serif', 'system-ui', 'sans-serif']).set(
        body_background_fill='#ffffff', body_background_fill_dark='#212121',
        block_background_fill='#ffffff', block_background_fill_dark='#212121',
        block_border_width='0px', block_shadow='none',
        button_primary_background_fill='#171717', button_primary_text_color='#ffffff',
        button_primary_background_fill_dark='#ececec', button_primary_text_color_dark='#171717',
        input_background_fill='#f4f4f4', input_background_fill_dark='#303030',
    )

CSS = """
.gradio-container { max-width: 1100px !important; margin: 0 auto; }
#app-header { padding: 18px 12px 10px; border-bottom: 1px solid var(--border-color-primary); }
#brand { font-size: 19px; font-weight: 650; letter-spacing: -.5px; }
#brand p { margin: 0; }
#brand small { font-size: 11px; font-weight: 450; opacity: .6; letter-spacing: .06em; }
#new-chat { max-width: 120px; min-width: 100px; border-radius: 12px; }
#chat-shell { width: 100%; max-width: 820px; margin: 0 auto; padding: 12px 16px 0; }
#conversation { border: none; background: transparent; }
#conversation .message { font-size: 15px; line-height: 1.75; }
#conversation .user { border-radius: 22px; }
#conversation .bot { background: transparent; border: none; }
#conversation .prose h1 { font-size: clamp(24px, 4vw, 34px); font-weight: 600; letter-spacing: -1px; }
#composer { border-radius: 26px !important; background: var(--input-background-fill); padding: 10px 16px; }
#composer textarea { font-size: 15px; }
#privacy-note { text-align: center; opacity: .65; font-size: 11px; padding: 4px 16px 12px; }
#privacy-note p { line-height: 1.6; }
#chat-shell .gallery, #chat-shell .dataset { border-radius: 16px; }
#chat-error { align-items: center; border: 1px solid #dc7373; border-radius: 14px;
  padding: 10px 14px; background: var(--input-background-fill); margin-bottom: 8px; }
#chat-error-message { flex: 1; min-width: 0; }
#chat-error-message p { margin: 0; font-size: 14px; }
#dismiss-chat-error { flex: 0 0 96px; min-height: 44px; font-size: 14px;
  background: transparent; border: none; cursor: pointer; }
#dismiss-chat-error:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
@media (max-width: 640px) {
  #chat-shell { padding: 4px 4px 0; }
  #app-header { padding: 12px 4px 8px; }
  #conversation { min-height: 300px; }
}
"""
