import csv
import json

from scraper.fetcher import Fetcher, FetchError
from scraper.crawler import crawl_company
from scraper.output import write_csv, write_json
from scraper.pipeline import Config, run
import pytest


def test_crawl_merges_subpages(acme_url, fetcher):
    c = crawl_company(acme_url, fetcher, max_pages=6)
    assert c.name == "Acme Cloud"
    assert c.emails[0] == "hello@acmecloud.eu"
    assert "+49 30 1234 5678" in c.phones
    assert len(c.pages_scraped) >= 4
    assert not any(u.endswith(".pdf") or "other.example.org" in u for u in c.pages_scraped)
    assert "Managed Kubernetes" in c.products_services
    assert any("GPU instances" in p for p in c.current_projects)
    assert {"Hetzner Cloud", "DigitalOcean"} <= set(c.competitors)


def test_max_pages_respected(acme_url, fetcher):
    assert len(crawl_company(acme_url, fetcher, max_pages=2).pages_scraped) == 2


def test_bare_site_warns_not_crashes(bare_url, fetcher):
    c = crawl_company(bare_url, fetcher)
    assert c.name == "Bare Co" and c.emails == ["info@bare.test"]
    assert "No phone found" in c.warnings


def test_robots_blocked(blocked_url, fetcher):
    with pytest.raises(FetchError, match="robots"):
        crawl_company(blocked_url, fetcher)


def test_unreachable_is_reported_not_raised(acme_url, fetcher):
    cos, fails = run(None, [acme_url, "http://127.0.0.1:9/", "not a url", acme_url], fetcher, Config())
    assert len(cos) == 1  # duplicate domain removed
    assert len(fails) == 2
    assert any("Invalid" in f["error"] or "Not a valid" in f["error"] for f in fails)
    assert any("127.0.0.1:9" in f["input"] for f in fails)


def test_query_path_uses_searcher(acme_url, fetcher):
    cos, _ = run("cloud startups", [], fetcher, Config(), searcher=lambda q, limit: [acme_url])
    assert [c.name for c in cos] == ["Acme Cloud"]


def test_search_failure_recorded(fetcher):
    def boom(q, limit):
        raise FetchError("Search failed: offline")
    cos, fails = run("cloud startups", [], fetcher, Config(), searcher=boom)
    assert cos == [] and "offline" in fails[0]["error"]


def test_output_levels(acme_url, fetcher, tmp_path):
    cos, fails = run(None, [acme_url], fetcher, Config())
    write_json(cos, fails, str(tmp_path / "o.json"), level=1)
    write_csv(cos, str(tmp_path / "o.csv"), level=2)
    j = json.loads((tmp_path / "o.json").read_text())
    assert "tech_stack" not in j["companies"][0] and "emails" in j["companies"][0]
    rows = list(csv.DictReader((tmp_path / "o.csv").open()))
    assert rows[0]["name"] == "Acme Cloud" and "tech_stack" not in rows[0] and "founded" in rows[0]


def test_search_parser():
    from scraper.search import parse_results
    html = '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Facme.io%2F&rut=1">A</a>'
    assert parse_results(html) == ["https://acme.io/"]
