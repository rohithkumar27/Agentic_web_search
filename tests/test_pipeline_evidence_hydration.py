from __future__ import annotations

from app.services.dedupe import EntityDeduper
from app.services.evidence_validator import EvidenceValidator
from app.services.extractor import ExtractedEntity, ExtractionOutput
from app.services.pipeline import SearchPipeline
from app.services.scoring import ConfidenceScorer


class _FakeSearchResult:
    def __init__(self, url: str) -> None:
        self.url = url


class _FakeSearchClient:
    def search(self, query: str, max_results: int):
        return [_FakeSearchResult("https://example.com/a")]


class _FakePage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.title = "Example"
        self.extraction_method = "trafilatura"


class _FakeScraper:
    def fetch_and_extract(self, url: str, cache=None):
        return _FakePage("Acme Health AI is a startup in Boston building clinical copilots.")


class _NoEvidenceExtractor:
    def extract(self, query: str, source_url: str, page_text: str, max_entities: int = 20) -> ExtractionOutput:
        return ExtractionOutput(
            entities=[
                ExtractedEntity(
                    entity_name="Acme Health AI",
                    category="startup",
                    description="Clinical copilot company",
                    website="https://acme.example.com",
                    location="Boston, MA",
                    field_evidence={},
                )
            ]
        )


def test_pipeline_hydrates_missing_evidence_before_validation() -> None:
    pipeline = SearchPipeline(
        search_client=_FakeSearchClient(),
        scraper=_FakeScraper(),
        extractor=_NoEvidenceExtractor(),
        evidence_validator=EvidenceValidator(),
        deduper=EntityDeduper(),
        scorer=ConfidenceScorer(),
        cache=None,
    )

    result = pipeline.run(query="AI startups in healthcare", max_results=1)

    assert len(result.entities) == 1
    entity = result.entities[0]
    assert "entity_name" in entity.field_evidence
    assert str(entity.field_evidence["entity_name"].source_url) == "https://example.com/a"

