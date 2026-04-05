from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=200)
    max_results: int = Field(default=10, ge=1, le=20)


class FieldEvidence(BaseModel):
    value: Any
    source_url: HttpUrl
    evidence_snippet: str = Field(min_length=1, max_length=500)


class EntityRecord(BaseModel):
    entity_id: str = Field(min_length=1, max_length=100)
    entity_name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    website: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=200)
    key_attributes: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(ge=0.0, le=1.0)
    sources: list[HttpUrl] = Field(default_factory=list)
    field_evidence: dict[str, FieldEvidence] = Field(default_factory=dict)


class RunMetrics(BaseModel):
    search_results_count: int = Field(ge=0)
    pages_crawled: int = Field(ge=0)
    tokens_used: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    latency_ms: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    run_id: str = Field(min_length=1)
    entities: list[EntityRecord] = Field(default_factory=list)
    metrics: RunMetrics
