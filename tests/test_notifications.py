import json

import notifications


def test_is_new_fault_true_when_transitioning_from_normal():
    assert notifications.is_new_fault("норма", "неисправность") is True


def test_is_new_fault_true_when_transitioning_from_warning():
    assert notifications.is_new_fault("предупреждение", "неисправность") is True


def test_is_new_fault_false_when_staying_in_fault():
    assert notifications.is_new_fault("неисправность", "неисправность") is False


def test_is_new_fault_false_when_not_fault():
    assert notifications.is_new_fault("норма", "норма") is False
    assert notifications.is_new_fault("норма", "предупреждение") is False


def test_is_new_fault_true_when_first_reading_is_already_fault():
    assert notifications.is_new_fault(None, "неисправность") is True


def test_is_new_fault_false_when_first_reading_is_not_fault():
    assert notifications.is_new_fault(None, "норма") is False


def test_send_telegram_alert_noop_without_credentials(monkeypatch):
    monkeypatch.setattr(notifications.config, "get", lambda key, default=None: default)

    called = []
    monkeypatch.setattr(notifications.urllib.request, "urlopen", lambda *a, **kw: called.append(1))

    notifications.send_telegram_alert("тест")

    assert called == []


def test_send_telegram_alert_posts_to_correct_url(monkeypatch):
    values = {"TELEGRAM_BOT_TOKEN": "123:ABC", "TELEGRAM_CHAT_ID": "999"}
    monkeypatch.setattr(notifications.config, "get", lambda key, default=None: values.get(key, default))

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["data"] = request.data
        captured["timeout"] = timeout

    monkeypatch.setattr(notifications.urllib.request, "urlopen", fake_urlopen)

    notifications.send_telegram_alert("Неисправность!")

    body = json.loads(captured["data"].decode())

    assert captured["url"] == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert body == {"chat_id": "999", "text": "Неисправность!", "parse_mode": "HTML"}
    assert captured["timeout"] == 5


def test_send_telegram_alert_uses_explicit_chat_id_when_given(monkeypatch):
    values = {"TELEGRAM_BOT_TOKEN": "123:ABC", "TELEGRAM_CHAT_ID": "999"}
    monkeypatch.setattr(notifications.config, "get", lambda key, default=None: values.get(key, default))

    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["data"] = request.data

    monkeypatch.setattr(notifications.urllib.request, "urlopen", fake_urlopen)

    notifications.send_telegram_alert("Проверьте оборудование.", chat_id="111")

    body = json.loads(captured["data"].decode())
    assert body["chat_id"] == "111"


def test_send_telegram_alert_swallows_network_errors(monkeypatch):
    values = {"TELEGRAM_BOT_TOKEN": "123:ABC", "TELEGRAM_CHAT_ID": "999"}
    monkeypatch.setattr(notifications.config, "get", lambda key, default=None: values.get(key, default))

    def raise_error(request, timeout=None):
        raise OSError("сеть недоступна")

    monkeypatch.setattr(notifications.urllib.request, "urlopen", raise_error)

    notifications.send_telegram_alert("Неисправность!")
