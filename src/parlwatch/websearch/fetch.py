"""Fetch a web page or PDF as clean text, safely.

The text comes from the open web, so it is untrusted: callers must present it to a model as data, never as instructions. Guards:
http(s) only on ports 80/443, hosts that resolve to public addresses only (no localhost, private or link-local ranges: checked on every
redirect hop), a size cap, a timeout, no cookies, and a clear user agent.
"""

import io
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from parlwatch.websearch.base import Page, SearchError

UA = "parlwatch-research/0.1 (+https://github.com/fredbuildsai/parlwatch)"
MAX_BYTES = 3_000_000


def check_public_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise SearchError(f"only http(s) URLs can be fetched: {url[:80]}")
    if u.port not in (None, 80, 443):
        raise SearchError(f"port {u.port} is not allowed")
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SearchError(f"cannot resolve {u.hostname}") from e
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise SearchError(f"{u.hostname} resolves to a non-public address; refused")


def _pdf_text(data: bytes, max_pages: int = 12) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [(p.extract_text() or "") for p in reader.pages[:max_pages]]
    meta = reader.metadata
    return (meta.title or "") if meta else "", "\n".join(pages).strip()


def fetch_page(url: str, max_chars: int = 6000, client: httpx.Client | None = None, timeout: float = 20.0) -> Page:
    own = client is None
    client = client or httpx.Client(timeout=timeout, headers={"User-Agent": UA}, follow_redirects=False)
    try:
        cur = url
        for _ in range(5):
            check_public_url(cur)
            with client.stream("GET", cur) as r:
                if r.is_redirect and r.headers.get("location"):
                    cur = urljoin(cur, r.headers["location"])
                    continue
                if r.status_code >= 400:
                    raise SearchError(f"HTTP {r.status_code} for {cur[:100]}")
                ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                body = b""
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                return _to_page(cur, ctype, body, max_chars)
        raise SearchError("too many redirects")
    except httpx.HTTPError as e:
        raise SearchError(f"fetch failed: {type(e).__name__}") from e
    finally:
        if own:
            client.close()


def _to_page(url: str, ctype: str, body: bytes, max_chars: int) -> Page:
    if ctype == "application/pdf" or body[:5] == b"%PDF-":
        title, text = _pdf_text(body)
        return Page(url, title, "", text[:max_chars], len(text) > max_chars, "application/pdf", "PDF: first 12 pages only")
    if ctype not in ("text/html", "application/xhtml+xml", "text/plain", ""):
        raise SearchError(f"unsupported content type {ctype}")
    html = body.decode("utf-8", errors="replace")
    if ctype == "text/plain":
        return Page(url, "", "", html[:max_chars], len(html) > max_chars, ctype)
    import trafilatura

    doc = trafilatura.bare_extraction(html, url=url, with_metadata=True, include_comments=False, include_tables=True)
    text = (getattr(doc, "text", "") or "").strip()
    if not text:
        raise SearchError("no readable text on the page (it may need JavaScript or block automated access)")
    return Page(url, (getattr(doc, "title", "") or "").strip(), (getattr(doc, "date", "") or "")[:10], text[:max_chars], len(text) > max_chars, ctype)
