"""HTTP layer: politeness (robots.txt, per-host delay), retries, size limits."""
from __future__ import annotations

import logging
import random
import time
from typing import Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

log = logging.getLogger(__name__)

DEFAULT_UA = "CompanyScraperBot/1.0 (+educational assignment)"
MAX_BYTES = 2_000_000


class FetchError(Exception):
    """Raised when a page cannot be retrieved (network, HTTP, robots, type)."""


class Fetcher:
    def __init__(self, delay: float = 1.0, jitter: float = 0.4,
                 timeout: float = 10.0, retries: int = 2,
                 user_agent: str = DEFAULT_UA, respect_robots: bool = True,
                 proxies: Dict[str, str] | None = None):
        self.delay, self.jitter = delay, jitter
        self.timeout, self.retries = timeout, retries
        self.respect_robots = respect_robots
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
            "Accept-Language": "en"})
        if proxies:
            self.session.proxies.update(proxies)
        self._last_hit: Dict[str, float] = {}
        self._robots: Dict[str, RobotFileParser | None] = {}

    def _throttle(self, host: str) -> None:
        wait = (self.delay + random.uniform(0, self.jitter)) if self.delay else 0
        elapsed = time.monotonic() - self._last_hit.get(host, 0)
        if elapsed < wait:
            time.sleep(wait - elapsed)
        self._last_hit[host] = time.monotonic()

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        p = urlparse(url)
        origin = f"{p.scheme}://{p.netloc}"
        if origin not in self._robots:
            rp = RobotFileParser()
            try:
                r = self.session.get(origin + "/robots.txt", timeout=self.timeout)
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                    self._robots[origin] = rp
                else:
                    self._robots[origin] = None  # no robots file => allowed
            except requests.RequestException:
                self._robots[origin] = None
        rp = self._robots[origin]
        return True if rp is None else rp.can_fetch(self.session.headers["User-Agent"], url)

    def get(self, url: str, expect_html: bool = True) -> requests.Response:
        if not self.allowed(url):
            raise FetchError(f"Blocked by robots.txt: {url}")
        host = urlparse(url).netloc
        last_err = "unknown error"
        for attempt in range(self.retries + 1):
            self._throttle(host)
            try:
                resp = self.session.get(url, timeout=self.timeout, stream=True)
                body = resp.raw.read(MAX_BYTES + 1, decode_content=True)
                resp._content = body[:MAX_BYTES]
                resp._content_consumed = True
            except requests.exceptions.SSLError as e:
                raise FetchError(f"SSL error for {url}: {e}") from e
            except requests.exceptions.RequestException as e:
                last_err = f"{type(e).__name__}: {e}"
                log.debug("Attempt %d failed for %s: %s", attempt + 1, url, last_err)
                time.sleep(min(2 ** attempt * 0.5, 4))
                continue
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = f"HTTP {resp.status_code}"
                time.sleep(min(2 ** attempt, 8))
                continue
            if resp.status_code >= 400:
                raise FetchError(f"HTTP {resp.status_code} for {url}")
            ctype = resp.headers.get("Content-Type", "")
            if expect_html and ctype and "html" not in ctype and "xml" not in ctype:
                raise FetchError(f"Non-HTML content ({ctype}) at {url}")
            return resp
        raise FetchError(f"Failed after {self.retries + 1} attempts: {url} ({last_err})")
