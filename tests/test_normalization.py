from app.services.normalization import (
    normalize_category,
    normalize_domain,
    normalize_location,
    normalize_name,
    normalize_website,
)


def test_normalize_name_equivalent_variants() -> None:
    assert normalize_name("Acme Health AI") == normalize_name("ACME-Health, AI")


def test_normalize_domain_and_website() -> None:
    assert normalize_domain("https://www.Example.com/products") == "example.com"
    assert normalize_website("http://www.Example.com") == "https://example.com"


def test_normalize_category_aliases() -> None:
    assert normalize_category("start-up") == "startup"
    assert normalize_category("OpenSource") == "open-source"


def test_normalize_location_spacing() -> None:
    assert normalize_location("  Boston,   MA  ") == "Boston, MA"
