from __future__ import annotations

import httpx
import pytest

from app.services.search_client import (
    SearchClient,
    SearchProviderAuthError,
    SearchProviderError,
    SearchProviderRateLimitError,
    SerpAPISearchProvider,
)


def test_search_provider_normalizes_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("q") == "open source database tools"
        assert request.url.params.get("num") == "2"
        return httpx.Response(
            200,
            json={
                "organic_results": [
                    {
                        "title": "PostgreSQL",
                        "link": "https://www.postgresql.org",
                        "snippet": "The world's most advanced open source database.",
                    },
                    {
                        "title": "ClickHouse",
                        "link": "https://clickhouse.com",
                        "snippet": "Fast open-source column-oriented DBMS.",
                    },
                    {
                        "title": "Ignored because max_results=2",
                        "link": "https://example.com/ignored",
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SerpAPISearchProvider(api_key="test", client=client)

    results = provider.search(query="open source database tools", max_results=2)

    assert len(results) == 2
    assert results[0].title == "PostgreSQL"
    assert str(results[0].url) == "https://www.postgresql.org/"
    assert results[0].source == "serpapi"
    assert results[1].rank == 2


def test_search_provider_requires_api_key() -> None:
    provider = SerpAPISearchProvider(api_key=None)
    with pytest.raises(SearchProviderAuthError):
        provider.search(query="ai startups", max_results=5)


def test_search_provider_maps_429() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limit"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SerpAPISearchProvider(api_key="test", client=client)

    with pytest.raises(SearchProviderRateLimitError):
        provider.search(query="ai startups", max_results=3)


def test_search_provider_retries_timeout_then_succeeds() -> None:
    attempts = {"count": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ReadTimeout("timeout")
        return httpx.Response(
            200,
            json={
                "organic_results": [
                    {
                        "title": "Acme Health",
                        "link": "https://acme-health.example.com",
                        "snippet": "Healthcare AI startup.",
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SerpAPISearchProvider(api_key="test", client=client, max_retries=2)

    results = provider.search(query="healthcare ai startups", max_results=1)

    assert attempts["count"] == 2
    assert len(results) == 1
    assert results[0].title == "Acme Health"


def test_search_client_delegates_to_provider() -> None:
    class StubProvider:
        def search(self, query: str, max_results: int):
            assert query == "top pizza places in Brooklyn"
            assert max_results == 1
            return []

    client = SearchClient(provider=StubProvider())
    assert client.search("top pizza places in Brooklyn", 1) == []


def test_search_provider_raises_after_exhausted_retries() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SerpAPISearchProvider(api_key="test", client=client, max_retries=1)

    with pytest.raises(SearchProviderError):
        provider.search(query="database tools", max_results=1)
