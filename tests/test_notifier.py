import json

import responses

from uptime_pinger.notifier import (
    DiscordNotifier,
    TelegramNotifier,
    notifiers_from_env,
)


def test_no_env_means_no_notifiers(monkeypatch):
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL"):
        monkeypatch.delenv(key, raising=False)
    assert notifiers_from_env() == []


def test_env_creates_both_notifiers(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.test/hook")

    names = [n.name for n in notifiers_from_env()]
    assert names == ["telegram", "discord"]


def test_telegram_needs_both_values(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "abc")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert notifiers_from_env() == []


@responses.activate
def test_telegram_sends_message():
    responses.post("https://api.telegram.org/botabc/sendMessage", json={"ok": True})
    assert TelegramNotifier("abc", "123").send("hello")

    body = json.loads(responses.calls[0].request.body)
    assert body == {"chat_id": "123", "text": "hello"}


@responses.activate
def test_discord_sends_message():
    responses.post("https://discord.test/hook", status=204)
    assert DiscordNotifier("https://discord.test/hook").send("hello")

    body = json.loads(responses.calls[0].request.body)
    assert body == {"content": "hello"}


@responses.activate
def test_failed_send_returns_false():
    responses.post("https://discord.test/hook", status=500)
    assert DiscordNotifier("https://discord.test/hook").send("hello") is False
