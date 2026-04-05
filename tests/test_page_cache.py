from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta

import httpx

from app.storage.page_cache import PageCache


def test_page_cache_roundtrip(tmp_path) -> None:
    cache = PageCache(cache_dir=tmp_path, ttl_seconds=3600)
    url = "https://example.com/a"

    cache.set(
        url=url,
        title="Example",
        text="Useful cleaned content for extraction.",
        extraction_method="trafilatura",
        raw_html="<html><body>Useful cleaned content for extraction.</body></html>",
    )

    cached = cache.get(url)
    assert cached is not None
    assert str(cached.url) == "https://example.com/a"
    assert cached.title == "Example"
    assert cached.raw_html.startswith("<html>")


def test_page_cache_expiry(tmp_path) -> None:
    cache = PageCache(cache_dir=tmp_path, ttl_seconds=10)
    url = "https://example.com/expired"

    entry = cache.set(
        url=url,
        title="Old",
        text="Old content",
        extraction_method="trafilatura",
        raw_html="<html>Old</html>",
    )

    # Force file payload to be expired.
    files = list(tmp_path.glob("*.json"))
    payload = entry.model_dump()
    payload["fetched_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    files[0].write_text(json.dumps(payload), encoding="utf-8")

    assert cache.get(url) is None


def test_page_cache_returns_none_for_corrupt_file(tmp_path) -> None:
    cache = PageCache(cache_dir=tmp_path, ttl_seconds=3600)
    url = "https://example.com/corrupt"

    cache.set(
        url=url,
        title="Bad",
        text="data",
        extraction_method="trafilatura",
        raw_html="<html>data</html>",
    )

    file_path = list(tmp_path.glob("*.json"))[0]
    file_path.write_text("not-json", encoding="utf-8")

    assert cache.get(url) is None


def test_repeat_read_from_cache_is_fast(tmp_path) -> None:
    cache = PageCache(cache_dir=tmp_path, ttl_seconds=3600)
    url = "https://example.com/fast"

    cache.set(
        url=url,
        title="Speed",
        text="x" * 500,
        extraction_method="trafilatura",
        raw_html="<html>" + ("x" * 500) + "</html>",
    )

    start_first = time.perf_counter()
    first = cache.get(url)
    first_elapsed = time.perf_counter() - start_first

    start_second = time.perf_counter()
    second = cache.get(url)
    second_elapsed = time.perf_counter() - start_second

    assert first is not None and second is not None
    assert second_elapsed <= first_elapsed * 1.5



def test_page_cache_key_is_stable_for_same_url(tmp_path) -> None:
    cache = PageCache(cache_dir=tmp_path, ttl_seconds=3600)
    url = "https://example.com/stable"

    cache.set(
        url=url,
        title="Stable",
        text="stable text",
        extraction_method="trafilatura",
        raw_html="<html>stable</html>",
    )

    files_after_first = sorted(p.name for p in tmp_path.glob("*.json"))

    cache.set(
        url=url,
        title="Stable 2",
        text="stable text 2",
        extraction_method="trafilatura",
        raw_html="<html>stable2</html>",
    )

    files_after_second = sorted(p.name for p in tmp_path.glob("*.json"))
    assert files_after_first == files_after_second
