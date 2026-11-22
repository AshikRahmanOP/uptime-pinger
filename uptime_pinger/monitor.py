"""The main loop: check every site, remember its state, alert on changes."""

import logging
import time

from .checker import CheckResult, check_site
from .config import Config
from .notifier import Notifier, broadcast

log = logging.getLogger(__name__)


def format_alert(result: CheckResult) -> str:
    """Build a human-friendly alert message."""
    site = result.site
    if result.is_up:
        return f"✅ RECOVERED: {site.name} is back up ({site.url}) in {result.response_ms} ms"
    return f"🔴 DOWN: {site.name} ({site.url}) - {result.error}"


class Monitor:
    """Keeps track of which sites are up or down between rounds.

    We only send an alert when a site's state CHANGES (up -> down or
    down -> up). Without this, a site that stays down would spam you
    with a message every round.
    """

    def __init__(self, config: Config, notifiers: list[Notifier]):
        self.config = config
        self.notifiers = notifiers
        self.last_state: dict[str, bool] = {}  # url -> was it up last time?

    def run_once(self) -> list[CheckResult]:
        """Check every site one time. Returns the results."""
        results = []
        for site in self.config.sites:
            result = check_site(site)
            results.append(result)
            self._log_result(result)
            self._maybe_alert(result)
        return results

    def run_forever(self) -> None:
        """Check all sites, sleep, repeat. Stop with Ctrl+C."""
        log.info(
            "Monitoring %d site(s) every %ds. Press Ctrl+C to stop.",
            len(self.config.sites),
            self.config.interval,
        )
        while True:
            self.run_once()
            time.sleep(self.config.interval)

    def _log_result(self, r: CheckResult) -> None:
        if r.is_up:
            log.info("UP    %-20s %s (%s, %s ms)", r.site.name, r.site.url, r.status_code, r.response_ms)
        else:
            log.warning("DOWN  %-20s %s (%s)", r.site.name, r.site.url, r.error)

    def _maybe_alert(self, r: CheckResult) -> None:
        url = r.site.url
        previous = self.last_state.get(url)
        self.last_state[url] = r.is_up

        if previous is None:
            # First time we see this site: alert only if it is already down.
            should_alert = not r.is_up
        else:
            should_alert = previous != r.is_up

        if should_alert:
            broadcast(self.notifiers, format_alert(r))
