from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, get_pipeline
from app.services.dedupe import EntityDeduper
from app.services.evidence_validator import EvidenceValidator
from app.services.extractor import ExtractedEntity, ExtractedFieldEvidence, ExtractionOutput
from app.services.pipeline import SearchPipeline
from app.services.scoring import ConfidenceScorer


class FakeSearchResult:
    def __init__(self, url: str):
        self.url = url


class FakeSearchClient:
    def search(self, query: str, max_results: int):
        assert query
        return [
            FakeSearchResult("https://example.com/a"),
            FakeSearchResult("https://example.com/b"),
        ][:max_results]


class FakePage:
    def __init__(self, text: str):
        self.text = text


class FakeScraper:
    def __init__(self, fail_url: str | None = None):
        self.fail_url = fail_url

    def fetch_and_extract(self, url: str, cache=None):
        if self.fail_url and url == self.fail_url:
            raise RuntimeError("forced scrape failure")
        return FakePage(text=f"content for {url}")


class FakeExtractor:
    def extract(self, query: str, source_url: str, page_text: str, max_entities: int = 20) -> ExtractionOutput:
        return ExtractionOutput(
            entities=[
                ExtractedEntity(
                    entity_name="Acme Health AI",
                    category="startup",
                    description="Clinical AI company",
                    website="https://acmehealth.ai/about",
                    location="Boston, MA",
                    key_attributes={"source_page": source_url},
                    field_evidence={
                        "entity_name": ExtractedFieldEvidence(
                            value="Acme Health AI",
                            source_url=source_url,
                            evidence_snippet="Acme Health AI is mentioned in this source.",
                        ),
                        "description": ExtractedFieldEvidence(
                            value="Clinical AI company",
                            source_url=source_url,
                            evidence_snippet="The company builds clinical AI tools.",
                        ),
                        "website": ExtractedFieldEvidence(
                            value="https://acmehealth.ai/about",
                            source_url=source_url,
                            evidence_snippet="Official website listed as acmehealth.ai.",
                        ),
                    },
                )
            ]
        )


def _pipeline(scraper: FakeScraper) -> SearchPipeline:
    return SearchPipeline(
        search_client=FakeSearchClient(),
        scraper=scraper,
        extractor=FakeExtractor(),
        evidence_validator=EvidenceValidator(),
        deduper=EntityDeduper(),
        scorer=ConfidenceScorer(),
        cache=None,
    )


def test_search_endpoint_orchestrates_pipeline_with_mocks() -> None:
    app.dependency_overrides[get_pipeline] = lambda: _pipeline(FakeScraper())
    try:
        client = TestClient(app)
        response = client.post("/search", json={"query": "ai startups in healthcare", "max_results": 2})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"].startswith("run_")
    assert payload["metrics"]["search_results_count"] == 2
    assert payload["metrics"]["pages_crawled"] == 2
    assert len(payload["entities"]) == 1
    assert payload["entities"][0]["entity_name"] == "Acme Health AI"


def test_search_endpoint_handles_partial_failures() -> None:
    app.dependency_overrides[get_pipeline] = lambda: _pipeline(FakeScraper(fail_url="https://example.com/b"))
    try:
        client = TestClient(app)
        response = client.post("/search", json={"query": "ai startups in healthcare", "max_results": 2})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"]["search_results_count"] == 2
    assert payload["metrics"]["pages_crawled"] == 1
    assert len(payload["entities"]) == 1
    assert any("scrape_failed[https://example.com/b]" in err for err in payload["metrics"]["errors"])
