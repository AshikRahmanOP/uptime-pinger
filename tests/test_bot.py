import ipaddress
import json

import pytest
import requests
import responses

from uptime_pinger import bot
from uptime_pinger.bot import TargetError, TelegramBot, handle_text, normalize_url

API = "https://api.telegram.org/botabc"


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    """Pretend every hostname resolves to a public IP, except 'localhost'-style names."""

    def resolve(host):
        if host in ("localhost", "internal.test"):
            return ["127.0.0.1"]
        try:
            return [str(ipaddress.ip_address(host))]  # IP literals resolve to themselves
        except ValueError:
            return ["93.184.216.34"]

    monkeypatch.setattr(bot, "_resolve_ips", resolve)


# ---------------------------------------------------------------- normalize_url


def test_adds_https_to_bare_domain():
    assert normalize_url("example.com") == "https://example.com"


def test_keeps_given_scheme_and_strips_discord_brackets():
    assert normalize_url("<http://example.com/path>") == "http://example.com/path"


def test_rejects_private_addresses():
    for target in ("localhost", "http://internal.test", "http://192.168.1.1", "http://[::1]"):
        with pytest.raises(TargetError):
            normalize_url(target)


def test_rejects_text_without_a_domain():
    with pytest.raises(TargetError):
        normalize_url("hello")


# ---------------------------------------------------------------- handle_text


@responses.activate
def test_plain_url_message_gets_up_reply():
    responses.get("https://example.com", status=200)
    reply = handle_text("example.com")
    assert reply.startswith("✅ example.com is UP: HTTP 200")


@responses.activate
def test_error_status_is_down():
    responses.get("https://example.com", status=503)
    assert handle_text("https://example.com").startswith("🔴 example.com is DOWN: HTTP 503")


@responses.activate
def test_no_response_is_down():
    responses.get("https://example.com", body=requests.ConnectionError("boom"))
    assert handle_text("example.com") == "🔴 example.com is DOWN: no response (ConnectionError)"


@responses.activate
def test_check_command_with_several_sites_and_bot_mention():
    responses.get("https://a.com", status=200)
    responses.get("https://b.com", status=500)
    reply = handle_text("<@123> /check a.com b.com")
    lines = reply.splitlines()
    assert lines[0].startswith("✅ a.com")
    assert lines[1].startswith("🔴 b.com")


def test_normal_chat_is_ignored():
    assert handle_text("hello there, how are you?") is None
    assert handle_text("check out example.com please") is None


def test_help_and_empty_check():
    assert "Send me a website" in handle_text("/start")
    assert "Send me a website" in handle_text("/help@MyUptimeBot")
    assert handle_text("/check").startswith("Usage")


def test_private_target_gets_warning_not_request():
    assert "not allowed" in handle_text("/check http://192.168.0.1")


@responses.activate
def test_too_many_urls_are_capped():
    for i in range(7):
        responses.get(f"https://s{i}.com", status=200)
    reply = handle_text(" ".join(f"s{i}.com" for i in range(7)))
    assert reply.startswith("Checking the first 5")
    assert len(responses.calls) == 5


# ---------------------------------------------------------------- Telegram


@responses.activate
def test_telegram_poll_replies_and_advances_offset():
    responses.get(
        f"{API}/getUpdates",
        json={
            "ok": True,
            "result": [
                {"update_id": 41, "message": {"message_id": 7, "chat": {"id": 99}, "text": "example.com"}},
                {"update_id": 42, "message": {"message_id": 8, "chat": {"id": 99}, "text": "just chatting"}},
            ],
        },
    )
    responses.get("https://example.com", status=200)
    responses.post(f"{API}/sendMessage", json={"ok": True})

    tg = TelegramBot("abc", poll_timeout=0)
    tg.poll_once()

    assert tg.offset == 43
    sends = [c for c in responses.calls if c.request.url.endswith("/sendMessage")]
    assert len(sends) == 1  # the chat message got no reply
    body = json.loads(sends[0].request.body)
    assert body["chat_id"] == 99
    assert body["reply_parameters"]["message_id"] == 7
    assert body["text"].startswith("✅ example.com is UP")


def test_run_bots_needs_a_token(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    assert bot.run_bots() == 2


# ---------------------------------------------------------------- Discord preflight

APP_URL = "https://discord.com/api/v10/applications/@me"


@responses.activate
def test_discord_preflight_ok_when_intent_on():
    responses.get(APP_URL, json={"flags": 1 << 19})
    assert bot.discord_preflight("tok") is None
    assert responses.calls[0].request.headers["Authorization"] == "Bot tok"


@responses.activate
def test_discord_preflight_reports_intent_off():
    responses.get(APP_URL, json={"flags": 0})
    assert "Message Content Intent" in bot.discord_preflight("tok")


@responses.activate
def test_discord_preflight_reports_bad_token():
    responses.get(APP_URL, status=401, json={"message": "401: Unauthorized"})
    assert "rejected" in bot.discord_preflight("tok")
