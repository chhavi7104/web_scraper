"""Input validation and normalisation."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse, urlunparse

_HOST_RE = re.compile(
    r"^(localhost|(\d{1,3}\.){3}\d{1,3}|([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63})$",
    re.I,
)


class InvalidInput(ValueError):
    pass


def normalize_url(raw: str) -> str:
    """Return a clean http(s) URL or raise InvalidInput.

    Bare domains such as ``example.com`` get ``https://`` prepended.
    """
    raw = (raw or "").strip()
    if not raw or re.search(r"\s", raw):
        raise InvalidInput(f"Not a valid URL: {raw!r}")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in ("http", "https"):
        raise InvalidInput(f"Unsupported scheme in {raw!r} (use http/https)")
    host = parsed.hostname or ""
    if not _HOST_RE.match(host):
        raise InvalidInput(f"Invalid host in {raw!r}")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(),
                       parsed.path or "/", "", parsed.query, ""))


def domain_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def classify_input(raw: str) -> str:
    """'url' if it looks like a URL/domain, otherwise 'query'."""
    try:
        normalize_url(raw)
        return "url"
    except InvalidInput:
        return "query"


def validate_query(query: Optional[str]) -> str:
    query = (query or "").strip()
    if len(query) < 3:
        raise InvalidInput("Search query must be at least 3 characters.")
    return query
