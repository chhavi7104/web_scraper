import pytest
from scraper.validate import InvalidInput, classify_input, domain_of, normalize_url, validate_query


@pytest.mark.parametrize("raw,expected", [
    ("example.com", "https://example.com/"),
    ("HTTP://Example.COM/path?x=1#frag", "http://example.com/path?x=1"),
    ("https://www.acme.io", "https://www.acme.io/"),
])
def test_normalize_ok(raw, expected):
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "ftp://x.com", "not a url", "http://", "http://bad_host", "nodots"])
def test_normalize_bad(raw):
    with pytest.raises(InvalidInput):
        normalize_url(raw)


def test_classify_and_query():
    assert classify_input("acme.com") == "url"
    assert classify_input("cloud computing startups in Europe") == "query"
    assert validate_query("  cloud startups ") == "cloud startups"
    with pytest.raises(InvalidInput):
        validate_query("ab")


def test_domain_of():
    assert domain_of("https://www.Acme.com/x") == "acme.com"
