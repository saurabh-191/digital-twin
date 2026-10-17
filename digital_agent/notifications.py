"""Optional Pushover notifications; no network calls on import."""
import logging
import os
import requests

def push(message):
    user, token = os.getenv('PUSHOVER_USER'), os.getenv('PUSHOVER_TOKEN')
    if not user or not token:
        return
    try:
        response = requests.post('https://api.pushover.net/1/messages.json',
            data={'user': user, 'token': token, 'message': message}, timeout=10)
        response.raise_for_status()
        if response.json().get("status") != 1:
            logging.getLogger(__name__).warning("Pushover rejected the notification")
    except (requests.RequestException, ValueError):
        logging.getLogger(__name__).warning('Pushover notification failed; saved data remains available')
