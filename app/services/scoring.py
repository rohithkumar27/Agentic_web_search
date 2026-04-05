from __future__ import annotations

from app.services.extractor import ExtractedEntity
from app.services.normalization import normalize_domain, normalize_name


class ConfidenceScorer:
    def score(self, entity: ExtractedEntity) -> float:
        evidence_quality = self._evidence_quality(entity)
        source_diversity = self._source_diversity(entity)
        agreement = self._agreement(entity)
        completeness = self._completeness(entity)
        contradiction_penalty = self._contradiction_penalty(entity)

        raw = (
            0.35 * evidence_quality
            + 0.25 * source_diversity
            + 0.25 * agreement
            + 0.15 * completeness
            - contradiction_penalty
        )

        return self._clamp(raw)

    def _evidence_quality(self, entity: ExtractedEntity) -> float:
        snippets = [len(ev.evidence_snippet) for ev in entity.field_evidence.values()]
        if not snippets:
            return 0.0
        avg_len = sum(snippets) / len(snippets)
        return self._clamp(avg_len / 220.0)

    def _source_diversity(self, entity: ExtractedEntity) -> float:
        domains = {normalize_domain(ev.source_url) for ev in entity.field_evidence.values()}
        domains.discard(None)
        if not domains:
            return 0.0
        return self._clamp(len(domains) / 3.0)

    def _agreement(self, entity: ExtractedEntity) -> float:
        comparable_fields = ("entity_name", "category", "description", "website", "location")
        agrees = 0
        total = 0

        for field_name in comparable_fields:
            value = getattr(entity, field_name)
            evidence = entity.field_evidence.get(field_name)
            if value is None or evidence is None:
                continue
            total += 1
            if normalize_name(str(value)) == normalize_name(str(evidence.value)):
                agrees += 1

        if total == 0:
            return 0.0
        return agrees / total

    def _completeness(self, entity: ExtractedEntity) -> float:
        fields = (entity.entity_name, entity.category, entity.description, entity.website, entity.location)
        populated = sum(1 for value in fields if value not in (None, ""))
        return populated / len(fields)

    def _contradiction_penalty(self, entity: ExtractedEntity) -> float:
        comparable_fields = ("category", "description", "website", "location")
        mismatches = 0
        for field_name in comparable_fields:
            value = getattr(entity, field_name)
            evidence = entity.field_evidence.get(field_name)
            if value is None or evidence is None:
                continue
            if normalize_name(str(value)) != normalize_name(str(evidence.value)):
                mismatches += 1
        return min(0.3, mismatches * 0.08)

    def _clamp(self, value: float) -> float:
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return round(value, 6)
