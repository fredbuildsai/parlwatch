import json

import httpx
import pytest

from parlwatch.websearch.base import Ledger, SearchError, SearchResult
from parlwatch.websearch.duckduckgo import DuckDuckGoSearcher
from parlwatch.websearch.fetch import _to_page, check_public_url, fetch_page

HTML = "<html><head><title>Press release</title></head><body><article><h1>Press release</h1><p>" + "OVHcloud announces a qualification. " * 12 + "</p></article></body></html>"


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "http://localhost/x", "https://10.0.0.5/a", "http://169.254.169.254/latest", "https://192.168.1.1/",
                                 "file:///etc/passwd", "ftp://example.org/x", "https://93.184.216.34:8443/x", "http://[::1]/"])
def test_unsafe_urls_refused(url):
    with pytest.raises(SearchError):
        check_public_url(url)


def test_public_ip_allowed():
    check_public_url("https://93.184.216.34/page")


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_fetch_page_extracts_text_and_follows_safe_redirect():
    def handler(req):
        if req.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://93.184.216.34/new"})
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, content=HTML.encode())

    p = fetch_page("https://93.184.216.34/old", max_chars=200, client=client_for(handler))
    assert p.url.endswith("/new") and "OVHcloud announces" in p.text and p.truncated and len(p.text) <= 200


def test_redirect_to_private_address_refused_and_errors_are_search_errors():
    redirect = lambda req: httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})  # noqa: E731
    with pytest.raises(SearchError, match="non-public|allowed"):
        fetch_page("https://93.184.216.34/x", client=client_for(redirect))
    with pytest.raises(SearchError, match="HTTP 404"):
        fetch_page("https://93.184.216.34/x", client=client_for(lambda req: httpx.Response(404)))
    with pytest.raises(SearchError, match="unsupported"):
        _to_page("https://93.184.216.34/x", "application/zip", b"PK", 100)
    with pytest.raises(SearchError, match="no readable text"):
        _to_page("https://93.184.216.34/x", "text/html", b"<html><body><script>app()</script></body></html>", 100)


class FakeDDG:
    def __init__(self, fail=0):
        self.fail, self.calls = fail, []

    def text(self, q, **kw):
        self.calls.append(("text", q, kw))
        if self.fail:
            self.fail -= 1
            raise RuntimeError("Ratelimit 202")
        return [{"title": " A ", "href": "https://a.example/x", "body": "snippet"}, {"title": "no url", "href": ""}]

    def news(self, q, **kw):
        self.calls.append(("news", q, kw))
        return [{"title": "N", "url": "https://n.example/y", "body": "b", "date": "2026-09-10T06:51:00+00:00", "source": "Src"}]


def test_duckduckgo_wrapper_maps_results_retries_and_validates():
    sleeps = []
    s = DuckDuckGoSearcher(min_interval=0, client=FakeDDG(fail=2), sleep=sleeps.append)
    r = s.search("q", region="fr-fr", recent="month")
    assert [x.url for x in r] == ["https://a.example/x"] and r[0].title == "A" and len(sleeps) >= 2
    assert s.client.calls[-1][2] == {"region": "fr-fr", "timelimit": "m", "max_results": 6}
    n = DuckDuckGoSearcher(min_interval=0, client=FakeDDG(), sleep=lambda x: None).search("q", kind="news")
    assert n[0].date == "2026-09-10" and n[0].source == "Src"
    with pytest.raises(SearchError, match="after 3 attempts"):
        DuckDuckGoSearcher(min_interval=0, client=FakeDDG(fail=9), sleep=lambda x: None).search("q")
    with pytest.raises(SearchError):
        DuckDuckGoSearcher(min_interval=0, client=FakeDDG(), sleep=lambda x: None).search("q", recent="decade")


def test_ledger_seen_fetched_and_budgets():
    led = Ledger(max_searches=1, max_fetches=1)
    led.searches.append({"results": [{"url": "https://A.example/x/"}]})
    led.fetches.append({"requested_url": "https://b.example/p#frag", "url": "https://b.example/p", "ok": True})
    led.fetches.append({"requested_url": "https://c.example/z", "url": "https://c.example/z", "ok": False})
    assert led.seen_urls() >= {"https://a.example/x", "https://b.example/p", "https://c.example/z"}
    assert led.fetched_urls() == {"https://b.example/p"}  # a failed fetch is seen but not read
    assert led.searches_left() == 0 and led.fetches_left() == -1
    assert json.loads(json.dumps(led.to_dict()))["max_searches"] == 1


def test_search_result_dataclass():
    assert SearchResult("t", "u", "s").date == ""
