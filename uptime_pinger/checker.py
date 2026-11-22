"""Check whether a website is up."""

import time
from dataclasses import dataclass

import requests

from .config import Site


@dataclass
class CheckResult:
    """The outcome of checking one site once."""

    site: Site
    is_up: bool
    status_code: int | None
    response_ms: float | None
    error: str | None = None


def check_site(site: Site) -> CheckResult:
    """Send an HTTP GET request to the site and report if it is up.

    A site counts as "up" when it answers with the expected status code
    before the timeout runs out.
    """
    start = time.perf_counter()
    try:
        response = requests.get(site.url, timeout=site.timeout)
    except requests.RequestException as exc:
        # Timeouts, DNS failures, refused connections, SSL errors, etc.
        return CheckResult(site, False, None, None, error=type(exc).__name__)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    is_up = response.status_code == site.expected_status
    error = None if is_up else f"Expected {site.expected_status}, got {response.status_code}"
    return CheckResult(site, is_up, response.status_code, elapsed_ms, error)
