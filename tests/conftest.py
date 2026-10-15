import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import fixtures  # noqa: E402


@pytest.fixture(scope="session")
def acme_url():
    srv, url = fixtures.make_server(fixtures.ACME)
    yield url
    srv.shutdown()


@pytest.fixture(scope="session")
def bare_url():
    srv, url = fixtures.make_server(fixtures.BARE)
    yield url
    srv.shutdown()


@pytest.fixture(scope="session")
def blocked_url():
    srv, url = fixtures.make_server(fixtures.ROBOTS_BLOCKED)
    yield url
    srv.shutdown()


@pytest.fixture
def fetcher():
    from scraper.fetcher import Fetcher
    return Fetcher(delay=0, jitter=0, timeout=3, retries=0)
