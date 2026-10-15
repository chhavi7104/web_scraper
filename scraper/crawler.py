"""Per-company crawler: homepage -> relevant internal pages (sitemap + link discovery)."""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from .extract import extract_page, soup_of
from .fetcher import Fetcher, FetchError
from .models import Company
from .validate import domain_of

log = logging.getLogger(__name__)

# page kind -> URL/anchor keywords; order = crawl priority
PAGE_KINDS = [
    ("contact", ("contact", "get-in-touch", "reach-us", "support")),
    ("about", ("about", "company", "who-we-are", "our-story", "team")),
    ("products", ("product", "service", "solution", "platform", "offering", "features")),
    ("projects", ("project", "case-stud", "customers", "research", "news", "blog", "press", "innovation")),
    ("other", ("careers", "jobs", "technology", "engineering", "compare", "vs", "alternative")),
]
LIST_FIELDS = ["emails", "phones", "products_services", "tech_stack", "current_projects", "competitors"]
SCALAR_FIELDS = ["address", "tagline", "description", "founded", "industry", "market_positioning"]


def classify_link(url: str, anchor: str) -> Optional[str]:
    path = urlparse(url).path.lower()
    hay = f"{path} {anchor.lower()}"
    if re.search(r"\.(pdf|jpe?g|png|gif|svg|zip|mp4|css|js)$", path):
        return None
    for kind, kws in PAGE_KINDS:
        if any(re.search(rf"(?<![a-z]){re.escape(k)}", hay) for k in kws):
            return kind
    return None


def sitemap_urls(fetcher: Fetcher, base: str) -> List[str]:
    try:
        xml = fetcher.get(base.rstrip("/") + "/sitemap.xml", expect_html=False).text
    except FetchError:
        return []
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)[:300]


def crawl_company(url: str, fetcher: Fetcher, max_pages: int = 6) -> Company:
    """Scrape a company's site. Raises FetchError only if the homepage is unreachable."""
    home = fetcher.get(url)
    home_url = home.url
    dom = domain_of(home_url)
    base = f"{urlparse(home_url).scheme}://{urlparse(home_url).netloc}"
    pages: List[tuple] = [("home", home_url, extract_page(home.text, home_url, "home"))]

    # Discover candidate internal pages from homepage links + sitemap.
    candidates: Dict[str, str] = {}
    cand_links = list(pages[0][2]["_links"]) + [(u, "") for u in sitemap_urls(fetcher, base)]
    for link, anchor in cand_links:
        if domain_of(link) != dom or link.rstrip("/") == home_url.rstrip("/"):
            continue
        kind = classify_link(link, anchor)
        if kind and link not in candidates:
            candidates[link] = kind
    order = {k: i for i, (k, _) in enumerate(PAGE_KINDS)}
    queue = sorted(candidates.items(), key=lambda kv: (order[kv[1]], len(kv[0])))
    # keep a spread of kinds rather than 6 blog posts
    chosen, per_kind = [], {}
    for link, kind in queue:
        if per_kind.get(kind, 0) < 2:
            chosen.append((link, kind))
            per_kind[kind] = per_kind.get(kind, 0) + 1
    warnings: List[str] = []
    for link, kind in chosen[: max(0, max_pages - 1)]:
        try:
            r = fetcher.get(link)
            pages.append((kind, r.url, extract_page(r.text, r.url, kind)))
        except FetchError as e:
            log.warning("Skipping subpage: %s", e)
            warnings.append(str(e))
    return merge_pages(home_url, pages, warnings)


def merge_pages(home_url: str, pages: List[tuple], warnings: List[str]) -> Company:
    c = Company(website=home_url, warnings=list(warnings))
    c.name = pages[0][2]["name"]
    c.pages_scraped = [u for _, u, _ in pages]
    for _, _, data in pages:
        for f in LIST_FIELDS:
            for item in data[f]:
                if item.lower() not in {x.lower() for x in getattr(c, f)}:
                    getattr(c, f).append(item)
        for net, link in data["social_profiles"].items():
            c.social_profiles.setdefault(net, link)
        for f in SCALAR_FIELDS:
            if data[f] and not getattr(c, f):
                setattr(c, f, data[f])
    # emails on the company's own domain first
    root = ".".join(domain_of(home_url).split(":")[0].split(".")[-2:])
    c.emails.sort(key=lambda e: 0 if e.split("@")[1].endswith(root) else 1)
    c.competitors = c.competitors[:10]
    for f in ("emails", "phones"):
        if not getattr(c, f):
            c.warnings.append(f"No {f[:-1]} found")
    return c
