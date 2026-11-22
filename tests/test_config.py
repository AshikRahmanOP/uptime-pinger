import pytest

from uptime_pinger.config import ConfigError, load_config


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_sites_with_defaults(tmp_path):
    path = write(tmp_path, "sites:\n  - url: https://example.com\n")
    config = load_config(path)

    assert config.interval == 60
    assert len(config.sites) == 1
    site = config.sites[0]
    assert site.name == "https://example.com"  # name falls back to the url
    assert site.expected_status == 200
    assert site.timeout == 10.0


def test_loads_custom_values(tmp_path):
    path = write(
        tmp_path,
        "interval: 30\nsites:\n  - name: API\n    url: http://api.local/health\n"
        "    expected_status: 204\n    timeout: 3\n",
    )
    config = load_config(path)

    assert config.interval == 30
    assert config.sites[0].name == "API"
    assert config.sites[0].expected_status == 204
    assert config.sites[0].timeout == 3.0


def test_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_config("does-not-exist.yaml")


def test_empty_sites_raises(tmp_path):
    with pytest.raises(ConfigError, match="non-empty"):
        load_config(write(tmp_path, "sites: []\n"))


def test_bad_url_raises(tmp_path):
    with pytest.raises(ConfigError, match="http"):
        load_config(write(tmp_path, "sites:\n  - url: example.com\n"))


def test_too_small_interval_raises(tmp_path):
    with pytest.raises(ConfigError, match="interval"):
        load_config(write(tmp_path, "interval: 1\nsites:\n  - url: https://a.com\n"))
