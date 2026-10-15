"""Search-query -> candidate company websites (DuckDuckGo HTML endpoint, no API key)."""
from __future__ import annotations

import logging
from typing import List
from urllib.parse import parse_qs, unquote, urlparse

import requests
from bs4 import BeautifulSoup

from .fetcher import DEFAULT_UA, FetchError
from .validate import domain_of

log = logging.getLogger(__name__)
SEARCH_URL = "https://html.duckduckgo.com/html/"

# Directories, social networks and media: useful as leads, but not company homepages.
SKIP_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "wikipedia.org", "crunchbase.com", "glassdoor.com", "indeed.com", "reddit.com", "quora.com",
    "medium.com", "forbes.com", "techcrunch.com", "g2.com", "capterra.com", "clutch.co",
    "pitchbook.com", "tracxn.com", "dealroom.co", "builtin.com", "github.com", "bloomberg.com",
    "startupblink.com", "f6s.com", "angel.co", "wellfound.com", "producthunt.com", "yelp.com",
    "duckduckgo.com", "google.com", "bing.com", "amazon.com", "pinterest.com", "tiktok.com",
}


def _unwrap(href: str) -> str:
    if "uddg=" in href:
        q = parse_qs(urlparse(href if "://" in href else "https:" + href).query)
        return unquote(q["uddg"][0]) if q.get("uddg") else href
    return href


def parse_results(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    urls = [_unwrap(a["href"]) for a in soup.select("a.result__a[href]")]
    return [u for u in urls if u.startswith("http")]


def search_companies(query: str, limit: int = 10, timeout: float = 15.0) -> List[str]:
    """Return up to ``limit`` distinct homepage URLs for the search query."""
    try:
        r = requests.post(SEARCH_URL, data={"q": query}, timeout=timeout,
                          headers={"User-Agent": DEFAULT_UA.replace("Bot", "") + " Mozilla/5.0"})
        r.raise_for_status()
    except requests.RequestException as e:
        raise FetchError(f"Search failed: {e}") from e
    seen, out = set(), []
    for url in parse_results(r.text):
        dom = domain_of(url)
        root = ".".join(dom.split(".")[-2:])
        if root in SKIP_DOMAINS or dom in seen:
            continue
        seen.add(dom)
        p = urlparse(url)
        out.append(f"{p.scheme}://{p.netloc}/")
        if len(out) >= limit:
            break
    log.info("Search %r -> %d candidate sites", query, len(out))
    return out
