from __future__ import annotations

import re
from urllib.parse import urlparse


_CATEGORY_ALIASES = {
    "startup": "startup",
    "start-up": "startup",
    "company": "company",
    "business": "company",
    "database": "database",
    "db": "database",
    "open source": "open-source",
    "opensource": "open-source",
}


def normalize_name(name: str) -> str:
    compact = re.sub(r"[^a-z0-9\s]", " ", name.lower())
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().strip()
    if not host:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_website(url: str | None) -> str | None:
    domain = normalize_domain(url)
    if not domain:
        return None
    return f"https://{domain}"


def normalize_category(category: str | None) -> str | None:
    if category is None:
        return None
    key = re.sub(r"\s+", " ", category.strip().lower())
    if not key:
        return None
    return _CATEGORY_ALIASES.get(key, key)


def normalize_location(location: str | None) -> str | None:
    if location is None:
        return None
    compact = re.sub(r"\s+", " ", location).strip()
    return compact or None
