"""Load and validate the list of sites to check from a YAML file."""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Site:
    """One website we want to monitor."""

    name: str
    url: str
    expected_status: int = 200
    timeout: float = 10.0


@dataclass
class Config:
    """All settings for a run."""

    sites: list[Site]
    interval: int = 60  # seconds between rounds of checks


class ConfigError(Exception):
    """Raised when the config file is missing or invalid."""


def load_config(path: str | Path) -> Config:
    """Read a YAML config file and turn it into a Config object."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_sites = data.get("sites")
    if not raw_sites:
        raise ConfigError("Config must contain a non-empty 'sites' list.")

    sites = []
    for i, item in enumerate(raw_sites, start=1):
        if not isinstance(item, dict) or "url" not in item:
            raise ConfigError(f"Site #{i} must have a 'url'.")
        url = str(item["url"])
        if not url.startswith(("http://", "https://")):
            raise ConfigError(f"Site #{i} url must start with http:// or https://")
        sites.append(
            Site(
                name=str(item.get("name", url)),
                url=url,
                expected_status=int(item.get("expected_status", 200)),
                timeout=float(item.get("timeout", 10)),
            )
        )

    interval = int(data.get("interval", 60))
    if interval < 5:
        raise ConfigError("'interval' must be at least 5 seconds.")

    return Config(sites=sites, interval=interval)
