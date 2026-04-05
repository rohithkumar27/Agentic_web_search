from __future__ import annotations

import httpx
import pytest

from app.services.scraper import ScrapeError, WebScraper
from app.storage.page_cache import PageCache


def test_fetch_and_extract_uses_trafilatura(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><head><title>Sample</title></head><body><article>ignored by mock</article></body></html>",
        )

    monkeypatch.setattr(
        "app.services.scraper.trafilatura.extract",
        lambda *args, **kwargs: (
            "Primary extracted content with enough text to pass the quality threshold "
            "and provide reliable downstream entity extraction for our pipeline checks."
        ),
    )

    scraper = WebScraper(client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = scraper.fetch_and_extract("https://example.com/post")

    assert result.extraction_method == "trafilatura"
    assert result.title == "Sample"
    assert "quality threshold" in result.text


def test_fetch_and_extract_falls_back_to_bs4(monkeypatch: pytest.MonkeyPatch) -> None:
    html = """
    <html>
      <head>
        <title>Fallback Title</title>
        <script>window.bad = true;</script>
      </head>
      <body>
        <main>
          <p>First paragraph of meaningful content.</p>
          <p>Second paragraph adds more details for extraction quality.</p>
        </main>
      </body>
    </html>
    """

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    monkeypatch.setattr("app.services.scraper.trafilatura.extract", lambda *args, **kwargs: None)

    scraper = WebScraper(client=httpx.Client(transport=httpx.MockTransport(handler)), min_text_length=20)
    result = scraper.fetch_and_extract("https://example.com/fallback")

    assert result.extraction_method == "beautifulsoup"
    assert "meaningful content" in result.text
    assert "window.bad" not in result.text


def test_fetch_and_extract_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    monkeypatch.setattr("app.services.scraper.trafilatura.extract", lambda *args, **kwargs: None)

    scraper = WebScraper(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ScrapeError):
        scraper.fetch_and_extract("https://example.com/down")


def test_fetch_and_extract_raises_on_short_content(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body><p>tiny</p></body></html>")

    monkeypatch.setattr("app.services.scraper.trafilatura.extract", lambda *args, **kwargs: "short")

    scraper = WebScraper(client=httpx.Client(transport=httpx.MockTransport(handler)), min_text_length=40)

    with pytest.raises(ScrapeError):
        scraper.fetch_and_extract("https://example.com/short")


def test_fetch_and_extract_uses_cache_without_network(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("network should not be called when cache has entry")

    monkeypatch.setattr("app.services.scraper.trafilatura.extract", lambda *args, **kwargs: None)

    cache = PageCache(cache_dir=tmp_path, ttl_seconds=3600)
    cache.set(
        url="https://example.com/cached",
        title="Cached Title",
        text=("Cached content " * 20).strip(),
        extraction_method="trafilatura",
        raw_html="<html>cached</html>",
    )

    scraper = WebScraper(client=httpx.Client(transport=httpx.MockTransport(handler)), min_text_length=20)
    result = scraper.fetch_and_extract("https://example.com/cached", cache=cache)

    assert result.extraction_method == "trafilatura:cache"
    assert result.title == "Cached Title"
    assert "Cached content" in result.text


def test_fetch_and_extract_second_run_is_faster_with_cache(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    html = "<html><head><title>Speed</title></head><body><p>" + ("word " * 80) + "</p></body></html>"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    monkeypatch.setattr(
        "app.services.scraper.trafilatura.extract",
        lambda *args, **kwargs: " ".join(["token"] * 140),
    )

    cache = PageCache(cache_dir=tmp_path, ttl_seconds=3600)
    scraper = WebScraper(client=httpx.Client(transport=httpx.MockTransport(handler)), min_text_length=50)

    import time

    t1 = time.perf_counter()
    first = scraper.fetch_and_extract("https://example.com/speed", cache=cache)
    first_elapsed = time.perf_counter() - t1

    t2 = time.perf_counter()
    second = scraper.fetch_and_extract("https://example.com/speed", cache=cache)
    second_elapsed = time.perf_counter() - t2

    assert first.extraction_method == "trafilatura"
    assert second.extraction_method.endswith(":cache")
    assert second_elapsed < first_elapsed
