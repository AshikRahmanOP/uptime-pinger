"""Chat bots: send a website URL in Telegram or Discord and get an up/down reply.

Run with:  python -m uptime_pinger --bot

A message that is only a URL (or a few URLs), or that starts with /check or
!check, gets a reply. Anything else is ignored, so the bot stays quiet in
normal conversation.
"""

import asyncio
import ipaddress
import logging
import os
import re
import socket
import threading
import time
from urllib.parse import urlparse

import requests

from .checker import check_site
from .config import Site

log = logging.getLogger(__name__)

MAX_URLS_PER_MESSAGE = 5
CHECK_TIMEOUT = 10  # seconds

HELP_TEXT = (
    "Send me a website and I'll tell you if it is up.\n\n"
    "Examples:\n"
    "  example.com\n"
    "  https://github.com\n"
    "  /check google.com python.org\n\n"
    f"Up to {MAX_URLS_PER_MESSAGE} sites per message."
)

# "example.com", "sub.example.co.uk:8080/path" ...
_DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}(?::\d+)?(?:[/?#]\S*)?$", re.I)
_MENTION_RE = re.compile(r"<@!?\d+>")  # Discord mentions like <@1234>


class TargetError(ValueError):
    """The text is not a URL we are willing to check."""


def _resolve_ips(host: str) -> list[str]:
    """Look up every IP address a hostname points to."""
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


def _is_public(ip: str) -> bool:
    return ipaddress.ip_address(ip.split("%")[0]).is_global


def looks_like_target(token: str) -> bool:
    token = token.strip("<>")
    return token.lower().startswith(("http://", "https://")) or bool(_DOMAIN_RE.match(token))


def normalize_url(token: str) -> str:
    """Turn user input like 'example.com' into 'https://example.com'.

    Refuses private, local and internal addresses so nobody can use the bot
    to poke at the network it runs on.
    """
    token = token.strip().strip("<>").rstrip(".,;!?)")
    if not token.lower().startswith(("http://", "https://")):
        token = "https://" + token

    parsed = urlparse(token)
    host = parsed.hostname
    if not host or ("." not in host and ":" not in host):
        raise TargetError("That doesn't look like a website address.")

    try:
        ips = _resolve_ips(host)
    except (socket.gaierror, UnicodeError):
        return token  # let the check itself report the DNS failure
    if not all(_is_public(ip) for ip in ips):
        raise TargetError("Private or local addresses are not allowed.")
    return token


def check_url(url: str) -> str:
    """Check one URL and build a one-line reply."""
    host = urlparse(url).hostname or url
    result = check_site(Site(name=host, url=url, timeout=CHECK_TIMEOUT))
    code = result.status_code

    if code is None:
        return f"🔴 {host} is DOWN: no response ({result.error})"
    if code < 400:
        return f"✅ {host} is UP: HTTP {code} in {result.response_ms} ms"
    return f"🔴 {host} is DOWN: HTTP {code} in {result.response_ms} ms"


def handle_text(text: str) -> str | None:
    """Decide how to answer a chat message. Returns None to stay quiet."""
    text = _MENTION_RE.sub("", text or "").strip()
    if not text:
        return None

    words = text.split()
    command = words[0].lower().split("@")[0]  # "/check@MyBot" -> "/check"

    if command in ("/start", "/help", "!help"):
        return HELP_TEXT
    if command in ("/check", "!check"):
        targets = words[1:]
        if not targets:
            return "Usage: /check example.com"
    elif all(looks_like_target(w) for w in words):
        targets = words
    else:
        return None  # normal chat, not for us

    lines = []
    if len(targets) > MAX_URLS_PER_MESSAGE:
        lines.append(f"Checking the first {MAX_URLS_PER_MESSAGE} sites only.")
        targets = targets[:MAX_URLS_PER_MESSAGE]

    for target in targets:
        try:
            url = normalize_url(target)
        except TargetError as exc:
            lines.append(f"⚠️ {target}: {exc}")
            continue
        lines.append(check_url(url))
    return "\n".join(lines)


# --------------------------------------------------------------------------- Telegram


class TelegramBot:
    """Reads new messages with long polling and replies to each one.

    Long polling means we ask Telegram "any new messages?" and it holds the
    request open for up to `poll_timeout` seconds until something arrives.
    No public server or webhook needed.
    """

    def __init__(self, token: str, poll_timeout: int = 30):
        self.api = f"https://api.telegram.org/bot{token}"
        self.poll_timeout = poll_timeout
        self.offset: int | None = None  # id of the next update we want

    def poll_once(self) -> None:
        r = requests.get(
            f"{self.api}/getUpdates",
            params={"timeout": self.poll_timeout, "offset": self.offset, "allowed_updates": '["message"]'},
            timeout=self.poll_timeout + 10,
        )
        r.raise_for_status()
        for update in r.json().get("result", []):
            self.offset = update["update_id"] + 1  # mark it as handled
            self.handle_update(update)

    def handle_update(self, update: dict) -> None:
        message = update.get("message") or {}
        reply = handle_text(message.get("text", ""))
        if reply:
            log.info("Telegram: answering a message in chat %s", message["chat"]["id"])
            self.send(message["chat"]["id"], reply, message.get("message_id"))

    def send(self, chat_id: int, text: str, reply_to: int | None = None) -> None:
        payload: dict = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if reply_to:
            payload["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
        try:
            requests.post(f"{self.api}/sendMessage", json=payload, timeout=10).raise_for_status()
        except requests.RequestException as exc:
            log.error("Telegram reply failed: %s", type(exc).__name__)

    def run_forever(self) -> None:
        log.info("Telegram bot is listening for messages.")
        while True:
            try:
                self.poll_once()
            except requests.RequestException as exc:
                # Log only the error type so the bot token never ends up in logs.
                log.error("Telegram polling failed: %s. Retrying in 5s.", type(exc).__name__)
                time.sleep(5)


# --------------------------------------------------------------------------- Discord


DISCORD_API = "https://discord.com/api/v10"
# Application flags meaning "Message Content Intent is switched on".
_MESSAGE_CONTENT_FLAGS = (1 << 18) | (1 << 19)


def discord_preflight(token: str) -> str | None:
    """Ask Discord if the token works and the bot may read messages.

    Returns an error message, or None if all is fine. Without this, a missing
    intent makes the bot reconnect forever with a confusing log line.
    """
    headers = {"Authorization": f"Bot {token}", "User-Agent": "DiscordBot (uptime-pinger, 1.0)"}
    try:
        r = requests.get(f"{DISCORD_API}/applications/@me", headers=headers, timeout=10)
    except requests.RequestException as exc:
        return f"Could not reach Discord: {type(exc).__name__}"
    if r.status_code == 401:
        return "Discord rejected DISCORD_BOT_TOKEN. Reset the token in the Developer Portal."
    if not r.ok:
        return f"Discord answered HTTP {r.status_code} when checking the bot."
    if not r.json().get("flags", 0) & _MESSAGE_CONTENT_FLAGS:
        return (
            "'Message Content Intent' is off, so the bot can't read messages. Turn it on in the "
            "Developer Portal (your app > Bot > Privileged Gateway Intents), save, then start again."
        )
    return None


class _DropVoiceWarnings(logging.Filter):
    """discord.py warns about voice libraries we never use. Hide that noise."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "voice will NOT be supported" not in record.getMessage()


def run_discord_bot(token: str) -> None:
    """Start the Discord bot. Blocks until stopped."""
    import discord  # imported here so Telegram-only setups don't need it loaded

    problem = discord_preflight(token)
    if problem:
        log.error("Discord bot not started: %s", problem)
        raise SystemExit(2)
    logging.getLogger("discord.client").addFilter(_DropVoiceWarnings())

    intents = discord.Intents.default()
    intents.message_content = True  # must also be switched on in the Developer Portal
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        log.info("Discord bot is listening as %s.", client.user)
        if not client.guilds:
            log.warning("The bot is not in any server yet. Invite it with the OAuth2 URL Generator.")

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return  # never answer bots, including ourselves
        # Checks use blocking HTTP, so run them in a thread to keep the bot responsive.
        reply = await asyncio.to_thread(handle_text, message.content)
        if reply:
            log.info("Discord: answering %s in #%s", message.author, message.channel)
            await message.reply(reply, mention_author=False, suppress_embeds=True)

    try:
        client.run(token, log_handler=None)  # use our own logging setup
    except discord.PrivilegedIntentsRequired:
        log.error("Discord bot stopped: 'Message Content Intent' is off in the Developer Portal.")
        raise SystemExit(2) from None


# --------------------------------------------------------------------------- start


def run_bots() -> int:
    """Start every bot that has a token in the environment."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    discord_token = os.getenv("DISCORD_BOT_TOKEN")

    if not telegram_token and not discord_token:
        log.error("Set TELEGRAM_BOT_TOKEN and/or DISCORD_BOT_TOKEN to run the bot.")
        return 2

    try:
        if telegram_token and discord_token:
            # Telegram polls in a background thread, Discord runs in the main thread.
            threading.Thread(target=TelegramBot(telegram_token).run_forever, daemon=True).start()
            run_discord_bot(discord_token)
        elif discord_token:
            run_discord_bot(discord_token)
        else:
            TelegramBot(telegram_token).run_forever()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    return 0
