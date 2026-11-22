"""Send alerts to Telegram and/or Discord."""

import logging
import os

import requests

log = logging.getLogger(__name__)


class Notifier:
    """Base class: every notifier has a send(message) method."""

    name = "base"

    def send(self, message: str) -> bool:
        raise NotImplementedError


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, message: str) -> bool:
        try:
            r = requests.post(self.url, json={"chat_id": self.chat_id, "text": message}, timeout=10)
            r.raise_for_status()
            return True
        except requests.RequestException as exc:
            # Log only the error type so the bot token never ends up in logs.
            log.error("Telegram alert failed: %s", type(exc).__name__)
            return False


class DiscordNotifier(Notifier):
    name = "discord"

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, message: str) -> bool:
        try:
            r = requests.post(self.webhook_url, json={"content": message}, timeout=10)
            r.raise_for_status()
            return True
        except requests.RequestException as exc:
            log.error("Discord alert failed: %s", type(exc).__name__)
            return False


def notifiers_from_env() -> list[Notifier]:
    """Create notifiers for whichever secrets are set in the environment."""
    notifiers: list[Notifier] = []

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        notifiers.append(TelegramNotifier(token, chat_id))

    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook:
        notifiers.append(DiscordNotifier(webhook))

    return notifiers


def broadcast(notifiers: list[Notifier], message: str) -> None:
    """Send one message through every configured notifier."""
    for n in notifiers:
        if n.send(message):
            log.info("Alert sent via %s", n.name)
