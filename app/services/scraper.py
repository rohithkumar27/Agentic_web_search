from __future__ import annotations

import re

import httpx
import trafilatura
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, HttpUrl

from app.storage.page_cache import PageCache


class ScrapeError(Exception):
    """Raised when a page cannot be scraped or extracted reliably."""


class ScrapedPage(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=500)
    text: str = Field(min_length=1)
    extraction_method: str = Field(min_length=1, max_length=50)


class WebScraper:
    def __init__(
        self,
        client: httpx.Client | None = None,
        timeout_seconds: float = 15.0,
        min_text_length: int = 120,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self._min_text_length = min_text_length

    def fetch_and_extract(self, url: str, cache: PageCache | None = None) -> ScrapedPage:
        if cache is not None:
            cached = cache.get(url)
            if cached is not None:
                return ScrapedPage(
                    url=cached.url,
                    title=cached.title,
                    text=cached.text,
                    extraction_method=f"{cached.extraction_method}:cache",
                )

        try:
            response = self._client.get(url)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ScrapeError("Network error while fetching page.") from exc

        if response.status_code >= 400:
            raise ScrapeError(f"Page fetch failed with status {response.status_code}.")

        html = response.text
        text = self._extract_with_trafilatura(html, response.url)
        method = "trafilatura"

        if not text:
            text = self._extract_with_bs4(html)
            method = "beautifulsoup"

        cleaned = self._clean_text(text)
        if len(cleaned) < self._min_text_length:
            raise ScrapeError("Extracted content is too short to be reliable.")

        title = self._extract_title(html)

        if cache is not None:
            cache.set(
                url=str(response.url),
                title=title,
                text=cleaned,
                extraction_method=method,
                raw_html=html,
            )

        return ScrapedPage(url=str(response.url), title=title, text=cleaned, extraction_method=method)

    def _extract_with_trafilatura(self, html: str, url: httpx.URL) -> str | None:
        return trafilatura.extract(
            html,
            url=str(url),
            include_links=False,
            include_formatting=False,
            favor_precision=True,
            deduplicate=True,
        )

    def _extract_with_bs4(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "footer", "nav", "aside"]):
            tag.decompose()
        return "\n".join(soup.stripped_strings)

    def _extract_title(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            return self._clean_text(soup.title.string)
        return None

    def _clean_text(self, text: str | None) -> str:
        if not text:
            return ""
        compact = re.sub(r"\s+", " ", text).strip()
        return compact
