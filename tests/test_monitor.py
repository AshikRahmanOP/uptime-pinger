import responses

from uptime_pinger.config import Config, Site
from uptime_pinger.monitor import Monitor
from uptime_pinger.notifier import Notifier

URL = "https://example.com"


class FakeNotifier(Notifier):
    """Collects messages in a list instead of sending them."""

    name = "fake"

    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)
        return True


def make_monitor():
    notifier = FakeNotifier()
    config = Config(sites=[Site(name="Example", url=URL)], interval=60)
    return Monitor(config, [notifier]), notifier


@responses.activate
def test_no_alert_when_site_is_up():
    responses.get(URL, status=200)
    monitor, notifier = make_monitor()

    monitor.run_once()
    monitor.run_once()

    assert notifier.messages == []


@responses.activate
def test_alerts_once_when_site_goes_down_then_recovers():
    monitor, notifier = make_monitor()

    responses.get(URL, status=200)
    monitor.run_once()  # up: no alert

    responses.replace(responses.GET, URL, status=503)
    monitor.run_once()  # down: alert
    monitor.run_once()  # still down: NO second alert (no spam)

    responses.replace(responses.GET, URL, status=200)
    monitor.run_once()  # back up: recovery alert

    assert len(notifier.messages) == 2
    assert "DOWN" in notifier.messages[0]
    assert "RECOVERED" in notifier.messages[1]


@responses.activate
def test_alerts_if_down_on_first_check():
    responses.get(URL, status=500)
    monitor, notifier = make_monitor()

    monitor.run_once()

    assert len(notifier.messages) == 1
    assert "DOWN" in notifier.messages[0]
