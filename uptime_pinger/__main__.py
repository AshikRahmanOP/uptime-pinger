"""Command-line entry point. Run with:  python -m uptime_pinger"""

import argparse
import logging
import sys

from dotenv import load_dotenv

from . import __version__
from .config import ConfigError, load_config
from .monitor import Monitor
from .notifier import notifiers_from_env


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="uptime-pinger",
        description="Check websites on a schedule and alert you when they go down.",
    )
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to the YAML config file.")
    parser.add_argument("--once", action="store_true", help="Check all sites one time and exit.")
    parser.add_argument(
        "--bot", action="store_true", help="Run the Telegram/Discord bot that answers URL checks in chat."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show debug logs.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("uptime_pinger")

    load_dotenv()  # read secrets from a .env file if one exists

    if args.bot:
        from .bot import run_bots

        return run_bots()

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2

    notifiers = notifiers_from_env()
    if notifiers:
        log.info("Alerts enabled: %s", ", ".join(n.name for n in notifiers))
    else:
        log.warning("No alert channel configured. Results will only be logged.")

    monitor = Monitor(config, notifiers)

    if args.once:
        results = monitor.run_once()
        # Exit code 1 if any site is down: handy for scripts and CI.
        return 0 if all(r.is_up for r in results) else 1

    try:
        monitor.run_forever()
    except KeyboardInterrupt:
        log.info("Stopped by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
