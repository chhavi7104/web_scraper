"""Orchestration: inputs -> validated URLs -> crawl -> results + failures."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .crawler import crawl_company
from .fetcher import Fetcher, FetchError
from .models import Company
from .search import search_companies
from .validate import InvalidInput, domain_of, normalize_url, validate_query

log = logging.getLogger(__name__)


@dataclass
class Config:
    max_companies: int = 10
    max_pages: int = 6
    level: int = 3


def resolve_targets(query: Optional[str], urls: List[str], cfg: Config,
                    searcher: Callable = search_companies) -> Tuple[List[str], List[dict]]:
    """Validate inputs and return (unique target URLs, failures)."""
    targets, failures, seen = [], [], set()

    def add(u: str) -> None:
        d = domain_of(u)
        if d not in seen:
            seen.add(d)
            targets.append(u)

    for raw in urls:
        try:
            add(normalize_url(raw))
        except InvalidInput as e:
            log.error("Invalid URL skipped: %s", e)
            failures.append({"input": raw, "error": str(e)})
    if query is not None:
        try:
            q = validate_query(query)
            for u in searcher(q, limit=cfg.max_companies):
                add(u)
        except (InvalidInput, FetchError) as e:
            log.error("Query failed: %s", e)
            failures.append({"input": query, "error": str(e)})
    return targets[: cfg.max_companies], failures


def run(query: Optional[str], urls: List[str], fetcher: Fetcher, cfg: Config,
        searcher: Callable = search_companies,
        progress: Optional[Callable[[int, int, str], None]] = None) -> Tuple[List[Company], List[dict]]:
    targets, failures = resolve_targets(query, urls, cfg, searcher)
    companies: List[Company] = []
    for i, url in enumerate(targets, 1):
        if progress:
            progress(i, len(targets), url)
        try:
            companies.append(crawl_company(url, fetcher, cfg.max_pages))
            log.info("Scraped %s (%d pages)", url, len(companies[-1].pages_scraped))
        except FetchError as e:
            log.error("Unreachable/unprocessable: %s", e)
            failures.append({"input": url, "error": str(e)})
        except Exception as e:  # never let one site kill the batch
            log.exception("Unexpected error for %s", url)
            failures.append({"input": url, "error": f"Unexpected {type(e).__name__}: {e}"})
    return companies, failures
