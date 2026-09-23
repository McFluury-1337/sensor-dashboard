import json
import urllib.request

import config

SEVERITY_FAULT = "неисправность"


def is_new_fault(previous_state, current_state):
    return current_state == SEVERITY_FAULT and previous_state != SEVERITY_FAULT


def send_telegram_alert(message):
    token = config.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode()
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )

    try:
        urllib.request.urlopen(request, timeout=5)
    except OSError:
        pass
