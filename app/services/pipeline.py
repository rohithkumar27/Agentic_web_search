from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.models.schemas import EntityRecord, FieldEvidence, RunMetrics, SearchResponse
from app.services.extractor import ExtractedFieldEvidence, ExtractedEntity, ExtractionOutput
from app.storage.page_cache import PageCache


logger = logging.getLogger(__name__)


class SearchLike(Protocol):
    def search(self, query: str, max_results: int): ...


class ScraperLike(Protocol):
    def fetch_and_extract(self, url: str, cache: PageCache | None = None): ...


class ExtractorLike(Protocol):
    def extract(self, query: str, source_url: str, page_text: str, max_entities: int = 20) -> ExtractionOutput: ...


class EvidenceValidatorLike(Protocol):
    def validate_and_prune(self, output: ExtractionOutput) -> ExtractionOutput: ...


class DeduperLike(Protocol):
    def dedupe(self, entities): ...


class ScorerLike(Protocol):
    def score(self, entity) -> float: ...


@dataclass
class SearchPipeline:
    search_client: SearchLike
    scraper: ScraperLike
    extractor: ExtractorLike
    evidence_validator: EvidenceValidatorLike
    deduper: DeduperLike
    scorer: ScorerLike
    cache: PageCache | None = None
    crawl_log_preview_chars: int = 700

    def run(self, query: str, max_results: int) -> SearchResponse:
        started = time.perf_counter()
        errors: list[str] = []
        pages_crawled = 0

        try:
            search_results = self.search_client.search(query=query, max_results=max_results)
        except Exception as exc:
            search_results = []
            errors.append(f"search_failed: {exc}")
            logger.warning("search_failed query=%s error=%s", query, exc)

        extracted_entities = []

        for result in search_results:
            url = str(result.url)
            try:
                page = self.scraper.fetch_and_extract(url, cache=self.cache)
                pages_crawled += 1
            except Exception as exc:
                errors.append(f"scrape_failed[{url}]: {exc}")
                logger.warning("scrape_failed url=%s error=%s", url, exc)
                continue

            text = str(getattr(page, "text", "") or "")
            title = str(getattr(page, "title", "") or "")
            extraction_method = str(getattr(page, "extraction_method", "unknown") or "unknown")
            preview = self._preview_text(text)

            logger.info(
                "crawl_extracted url=%s method=%s title=%s text_len=%d preview=%s",
                url,
                extraction_method,
                title,
                len(text),
                preview,
            )

            try:
                extraction = self.extractor.extract(
                    query=query,
                    source_url=url,
                    page_text=text,
                    max_entities=20,
                )
            except Exception as exc:
                errors.append(f"extract_failed[{url}]: {exc}")
                logger.warning("extract_failed url=%s error=%s", url, exc)
                continue

            extraction = self._hydrate_missing_evidence(extraction=extraction, source_url=url, page_text=text)
            validated = self.evidence_validator.validate_and_prune(extraction)
            logger.info(
                "extraction_result url=%s raw_entities=%d validated_entities=%d",
                url,
                len(extraction.entities),
                len(validated.entities),
            )
            extracted_entities.extend(validated.entities)

        merged_entities = self.deduper.dedupe(extracted_entities)

        records: list[EntityRecord] = []
        for idx, entity in enumerate(merged_entities, start=1):
            field_evidence: dict[str, FieldEvidence] = {}
            sources: list[str] = []

            for field_name, evidence in entity.field_evidence.items():
                try:
                    field_evidence[field_name] = FieldEvidence(
                        value=evidence.value,
                        source_url=evidence.source_url,
                        evidence_snippet=evidence.evidence_snippet,
                    )
                    sources.append(evidence.source_url)
                except Exception as exc:
                    errors.append(f"evidence_invalid[{entity.entity_name}.{field_name}]: {exc}")
                    logger.warning(
                        "evidence_invalid entity=%s field=%s error=%s",
                        entity.entity_name,
                        field_name,
                        exc,
                    )

            unique_sources = sorted(set(sources))
            confidence = self.scorer.score(entity)

            records.append(
                EntityRecord(
                    entity_id=f"ent_{idx}",
                    entity_name=entity.entity_name,
                    category=entity.category,
                    description=entity.description,
                    website=entity.website,
                    location=entity.location,
                    key_attributes=entity.key_attributes,
                    confidence_score=confidence,
                    sources=unique_sources,
                    field_evidence=field_evidence,
                )
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        metrics = RunMetrics(
            search_results_count=len(search_results),
            pages_crawled=pages_crawled,
            tokens_used=0,
            estimated_cost=0.0,
            latency_ms=latency_ms,
            errors=errors,
        )

        return SearchResponse(
            run_id=f"run_{uuid.uuid4().hex[:10]}",
            entities=records,
            metrics=metrics,
        )

    def _preview_text(self, text: str) -> str:
        compact = " ".join(text.split())
        if len(compact) <= self.crawl_log_preview_chars:
            return compact
        return compact[: self.crawl_log_preview_chars] + "..."

    def _hydrate_missing_evidence(self, extraction: ExtractionOutput, source_url: str, page_text: str) -> ExtractionOutput:
        hydrated_entities: list[ExtractedEntity] = []
        for entity in extraction.entities:
            evidence_map = dict(entity.field_evidence)
            for field_name in ("entity_name", "category", "description", "website", "location"):
                value = getattr(entity, field_name)
                if value in (None, ""):
                    continue
                if field_name in evidence_map:
                    continue
                snippet = self._extract_snippet(page_text, str(value))
                evidence_map[field_name] = ExtractedFieldEvidence(
                    value=value,
                    source_url=source_url,
                    evidence_snippet=snippet,
                )

            hydrated_entities.append(
                ExtractedEntity(
                    entity_name=entity.entity_name,
                    category=entity.category,
                    description=entity.description,
                    website=entity.website,
                    location=entity.location,
                    key_attributes=entity.key_attributes,
                    field_evidence=evidence_map,
                )
            )

        return ExtractionOutput(entities=hydrated_entities)

    def _extract_snippet(self, text: str, target: str, max_len: int = 240) -> str:
        compact = " ".join(text.split())
        if not compact:
            return target[:max_len]

        lower = compact.lower()
        needle = target.strip().lower()
        if needle:
            idx = lower.find(needle)
            if idx != -1:
                start = max(0, idx - 80)
                end = min(len(compact), idx + len(needle) + 80)
                return compact[start:end][:max_len]

        return compact[:max_len]
