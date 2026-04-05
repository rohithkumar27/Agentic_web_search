from app.models.schemas import EntityRecord, FieldEvidence, RunMetrics, SearchRequest, SearchResponse
import pytest
from pydantic import ValidationError


def test_search_request_valid() -> None:
    payload = SearchRequest(query="AI startups in healthcare", max_results=8)
    assert payload.query == "AI startups in healthcare"
    assert payload.max_results == 8


def test_search_request_invalid_max_results() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="ok query", max_results=100)


def test_entity_record_valid() -> None:
    entity = EntityRecord(
        entity_id="ent_1",
        entity_name="Acme Health AI",
        category="startup",
        description="Clinical workflow assistant",
        website="https://acme.example.com",
        location="Boston, MA",
        key_attributes={"founded": 2021},
        confidence_score=0.82,
        sources=["https://source.example.com/article"],
        field_evidence={
            "entity_name": FieldEvidence(
                value="Acme Health AI",
                source_url="https://source.example.com/article",
                evidence_snippet="Acme Health AI launched a new product.",
            )
        },
    )
    assert entity.confidence_score == 0.82


def test_entity_record_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        EntityRecord(
            entity_id="ent_1",
            entity_name="Bad Entity",
            confidence_score=1.8,
        )


def test_search_response_valid() -> None:
    resp = SearchResponse(
        run_id="run_1",
        entities=[],
        metrics=RunMetrics(
            search_results_count=10,
            pages_crawled=8,
            tokens_used=1200,
            estimated_cost=0.07,
            latency_ms=1420,
            errors=[],
        ),
    )
    assert resp.metrics.pages_crawled == 8
