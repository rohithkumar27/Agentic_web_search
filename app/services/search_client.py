from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field, HttpUrl


class SearchResult(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl
    snippet: str | None = Field(default=None, max_length=1000)
    rank: int = Field(ge=1)
    source: str = Field(min_length=1, max_length=50)


class SearchProviderError(Exception):
    """Base exception for search provider issues."""


class SearchProviderAuthError(SearchProviderError):
    """Raised when provider credentials are missing or invalid."""


class SearchProviderRateLimitError(SearchProviderError):
    """Raised when provider rate limits are exceeded."""


class SearchProvider:
    """Interface for provider implementations."""

    name: str

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        raise NotImplementedError


class SerpAPISearchProvider(SearchProvider):
    name = "serpapi"
    _endpoint = "https://serpapi.com/search.json"

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 15.0,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("SERPAPI_API_KEY")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        if not self._api_key:
            raise SearchProviderAuthError("SERPAPI_API_KEY is not configured.")

        params = {
            "q": query,
            "num": max_results,
            "engine": "google",
            "api_key": self._api_key,
        }

        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                response = self._client.get(self._endpoint, params=params)
                self._raise_for_status(response)
                payload = response.json()
                return self._normalize_results(payload.get("organic_results", []), max_results)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                continue
            except ValueError as exc:
                raise SearchProviderError("Search provider returned invalid JSON.") from exc

        raise SearchProviderError("Search provider request failed after retries.") from last_error

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise SearchProviderAuthError("Search provider authentication failed.")
        if response.status_code == 429:
            raise SearchProviderRateLimitError("Search provider rate limit exceeded.")
        if response.status_code >= 500:
            raise SearchProviderError("Search provider server error.")
        if response.status_code >= 400:
            raise SearchProviderError(f"Search provider request failed with status {response.status_code}.")

    def _normalize_results(self, organic_results: list[dict[str, Any]], max_results: int) -> list[SearchResult]:
        normalized: list[SearchResult] = []
        for idx, row in enumerate(organic_results[:max_results], start=1):
            link = row.get("link")
            title = (row.get("title") or "").strip()
            if not link or not title:
                continue
            normalized.append(
                SearchResult(
                    title=title,
                    url=link,
                    snippet=(row.get("snippet") or None),
                    rank=idx,
                    source=self.name,
                )
            )
        return normalized


class SearchClient:
    """Facade to keep upstream pipeline provider-agnostic."""

    def __init__(self, provider: SearchProvider) -> None:
        self._provider = provider

    def search(self, query: str, max_results: int) -> list[SearchResult]:
        return self._provider.search(query=query, max_results=max_results)
