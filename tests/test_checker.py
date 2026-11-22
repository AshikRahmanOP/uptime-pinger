import requests
import responses

from uptime_pinger.checker import check_site
from uptime_pinger.config import Site

URL = "https://example.com"


@responses.activate
def test_site_is_up_on_expected_status():
    responses.get(URL, status=200)
    result = check_site(Site(name="Example", url=URL))

    assert result.is_up
    assert result.status_code == 200
    assert result.response_ms is not None
    assert result.error is None


@responses.activate
def test_site_is_down_on_wrong_status():
    responses.get(URL, status=500)
    result = check_site(Site(name="Example", url=URL))

    assert not result.is_up
    assert result.status_code == 500
    assert "got 500" in result.error


@responses.activate
def test_custom_expected_status():
    responses.get(URL, status=204)
    result = check_site(Site(name="Example", url=URL, expected_status=204))

    assert result.is_up


@responses.activate
def test_connection_error_means_down():
    responses.get(URL, body=requests.ConnectionError("boom"))
    result = check_site(Site(name="Example", url=URL))

    assert not result.is_up
    assert result.status_code is None
    assert result.error == "ConnectionError"


@responses.activate
def test_timeout_means_down():
    responses.get(URL, body=requests.Timeout())
    result = check_site(Site(name="Example", url=URL))

    assert not result.is_up
    assert result.error == "Timeout"
