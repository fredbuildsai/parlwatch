"""DuckDuckGo search through the `ddgs` library.

DuckDuckGo has no official search API: `ddgs` queries its public endpoints, so it can be rate-limited or change without notice.
Requests are spaced (>= `min_interval` seconds) and retried with back-off. Swap in another `Searcher` (SearXNG, Brave, Tavily...)
if reliability or terms of use matter more than convenience.
"""

import time

from parlwatch.websearch.base import Kind, SearchError, SearchResult

TIMELIMIT = {"any": None, "day": "d", "week": "w", "month": "m", "year": "y"}


class DuckDuckGoSearcher:
    name = "duckduckgo"

    def __init__(self, min_interval: float = 2.0, retries: int = 3, client=None, sleep=time.sleep):
        self.min_interval, self.retries, self._client, self._last, self._sleep = min_interval, retries, client, 0.0, sleep

    @property
    def client(self):
        if self._client is None:
            from ddgs import DDGS

            self._client = DDGS()
        return self._client

    def search(self, query: str, kind: Kind = "web", region: str = "wt-wt", recent: str = "any", max_results: int = 6) -> list[SearchResult]:
        if recent not in TIMELIMIT:
            raise SearchError(f"recent must be one of {list(TIMELIMIT)}")
        err = ""
        for attempt in range(1, self.retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
            self._last = time.monotonic()
            try:
                if kind == "news":
                    rows = self.client.news(query, region=region, timelimit=TIMELIMIT[recent], max_results=max_results)
                else:
                    rows = self.client.text(query, region=region, timelimit=TIMELIMIT[recent], max_results=max_results)
                return [self._row(r) for r in rows if (r.get("href") or r.get("url"))]
            except Exception as e:  # ddgs raises several library-specific exception types
                err = f"{type(e).__name__}: {str(e)[:120]}"
                if "No results" in str(e):
                    return []
                self._sleep(min(2.0 * attempt, 6.0))
        raise SearchError(f"DuckDuckGo search failed after {self.retries} attempts ({err})", retryable=True)

    @staticmethod
    def _row(r: dict) -> SearchResult:
        return SearchResult(title=(r.get("title") or "").strip(), url=(r.get("href") or r.get("url") or "").strip(),
                            snippet=(r.get("body") or "").strip()[:400], date=(r.get("date") or "")[:10], source=r.get("source") or "")
