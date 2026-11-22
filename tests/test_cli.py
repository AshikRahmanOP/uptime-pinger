import responses

from uptime_pinger.__main__ import main


def write_config(tmp_path, url):
    path = tmp_path / "config.yaml"
    path.write_text(f"sites:\n  - name: Test\n    url: {url}\n", encoding="utf-8")
    return str(path)


@responses.activate
def test_once_returns_0_when_all_up(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    responses.get("https://ok.test", status=200)

    assert main(["--config", write_config(tmp_path, "https://ok.test"), "--once"]) == 0


@responses.activate
def test_once_returns_1_when_a_site_is_down(tmp_path, monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    responses.get("https://bad.test", status=500)

    assert main(["--config", write_config(tmp_path, "https://bad.test"), "--once"]) == 1


def test_bad_config_returns_2(tmp_path):
    assert main(["--config", str(tmp_path / "missing.yaml"), "--once"]) == 2
