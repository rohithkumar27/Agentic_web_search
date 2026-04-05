from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl


class CachedPage(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=500)
    text: str = Field(min_length=1)
    extraction_method: str = Field(min_length=1, max_length=50)
    raw_html: str = Field(min_length=1)
    fetched_at: datetime


class PageCache:
    def __init__(self, cache_dir: str | Path = ".cache/pages", ttl_seconds: int = 3600) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, url: str) -> CachedPage | None:
        path = self._path_for_url(url)
        if not path.exists():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cached = CachedPage.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            return None

        if self._is_expired(cached.fetched_at):
            return None

        return cached

    def set(
        self,
        url: str,
        title: str | None,
        text: str,
        extraction_method: str,
        raw_html: str,
    ) -> CachedPage:
        cached = CachedPage(
            url=url,
            title=title,
            text=text,
            extraction_method=extraction_method,
            raw_html=raw_html,
            fetched_at=datetime.now(UTC),
        )
        path = self._path_for_url(url)
        path.write_text(cached.model_dump_json(), encoding="utf-8")
        return cached

    def _path_for_url(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{key}.json"

    def _is_expired(self, fetched_at: datetime) -> bool:
        now = datetime.now(UTC)
        # Pydantic should parse timezone-aware datetime from our stored payload.
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        return now - fetched_at > self._ttl
