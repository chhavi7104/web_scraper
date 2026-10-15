from scraper.extract import (extract_competitors, extract_page, extract_phones, extract_positioning,
                             soup_of)
import fixtures


def test_homepage_signals():
    d = extract_page(fixtures.ACME["/"], "https://acmecloud.eu/")
    assert d["name"] == "Acme Cloud"
    assert d["founded"] == "2016"
    assert "Berlin" in d["address"]
    assert {"React", "Google Analytics", "AWS", "OpenStack", "Kubernetes", "PostgreSQL"} <= set(d["tech_stack"])
    assert d["social_profiles"]["linkedin"].endswith("/company/acme-cloud")
    assert "twitter" in d["social_profiles"]
    assert d["industry"] == "Cloud Computing"
    assert d["market_positioning"].startswith("Market leader")


def test_competitors():
    c = extract_competitors("Looking for an alternative to Hetzner Cloud? Acme vs DigitalOcean: compare.", "Acme")
    assert "Hetzner Cloud" in c and "DigitalOcean" in c


def test_contact_filters_noise():
    d = extract_page(fixtures.ACME["/contact"], "https://acmecloud.eu/contact", "contact")
    assert d["emails"] == ["hello@acmecloud.eu", "sales@acmecloud.eu"]  # no logo@2x.png
    assert d["phones"] == ["+49 30 1234 5678"]  # order number ignored


def test_phone_tel_link_and_date_rejected():
    s = soup_of('<a href="tel:+1-555-010-9999">x</a><p>Posted 2024-01-02</p>')
    assert extract_phones(s) == ["+1-555-010-9999"]


def test_projects_and_products_on_kind_pages():
    about = extract_page(fixtures.ACME["/about"], "https://a.eu/about", "about")
    assert any("sovereign object-storage" in p for p in about["current_projects"])
    prod = extract_page(fixtures.ACME["/products"], "https://a.eu/products", "products")
    assert prod["products_services"] == ["Compute Instances", "Managed Kubernetes", "Object Storage"]


def test_positioning_empty_when_no_signal():
    assert extract_positioning("We sell shoes.") == ""
