"""Web search interface. Providers are pluggable; DuckDuckGo is the default (no key needed)."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

Kind = Literal["web", "news"]


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    date: str = ""  # ISO date when the provider gives one (news results do)
    source: str = ""


@dataclass
class SearchError(Exception):
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return self.message


class Searcher(Protocol):
    name: str

    def search(self, query: str, kind: Kind = "web", region: str = "wt-wt", recent: str = "any", max_results: int = 6) -> list[SearchResult]: ...


@dataclass
class Page:
    url: str  # final URL after redirects
    title: str
    date: str
    text: str
    truncated: bool
    content_type: str = "text/html"
    note: str = ""


@dataclass
class Ledger:
    """Everything the agent searched and read in one run. Used to check its citations and to enforce budgets in code."""

    max_searches: int | None = None
    max_fetches: int | None = None
    searches: list[dict] = field(default_factory=list)
    fetches: list[dict] = field(default_factory=list)

    @staticmethod
    def norm(u: str) -> str:
        return u.split("#")[0].rstrip("/").lower()

    def searches_left(self) -> int | None:
        return None if self.max_searches is None else self.max_searches - len(self.searches)

    def fetches_left(self) -> int | None:
        return None if self.max_fetches is None else self.max_fetches - len(self.fetches)

    def seen_urls(self) -> set[str]:
        """URLs returned by a search or read by a fetch (this run only)."""
        urls = {self.norm(r["url"]) for s in self.searches for r in s["results"]}
        return urls | {self.norm(f["requested_url"]) for f in self.fetches} | {self.norm(f["url"]) for f in self.fetches if f.get("url")}

    def fetched_urls(self) -> set[str]:
        """URLs whose content was actually read."""
        out = set()
        for f in self.fetches:
            if f["ok"]:
                out |= {self.norm(f["requested_url"]), self.norm(f["url"])}
        return out

    def to_dict(self) -> dict:
        return {"max_searches": self.max_searches, "max_fetches": self.max_fetches, "searches": self.searches, "fetches": self.fetches}
