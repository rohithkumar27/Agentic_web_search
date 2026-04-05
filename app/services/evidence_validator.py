from __future__ import annotations

import re

from app.services.extractor import ExtractedEntity, ExtractedFieldEvidence, ExtractionOutput


EVIDENCE_REQUIRED_FIELDS = ("entity_name", "category", "description", "website", "location")


class EvidenceValidator:
    def __init__(self, snippet_max_length: int = 240) -> None:
        self._snippet_max_length = snippet_max_length

    def validate_and_prune(self, output: ExtractionOutput) -> ExtractionOutput:
        validated: list[ExtractedEntity] = []
        for entity in output.entities:
            pruned = self._prune_entity(entity)
            if pruned is not None:
                validated.append(pruned)
        return ExtractionOutput(entities=validated)

    def _prune_entity(self, entity: ExtractedEntity) -> ExtractedEntity | None:
        data = entity.model_dump()
        evidence_map = dict(entity.field_evidence)

        for field_name in EVIDENCE_REQUIRED_FIELDS:
            value = data.get(field_name)
            if value is None:
                continue

            raw_evidence = evidence_map.get(field_name)
            if raw_evidence is None:
                if field_name == "entity_name":
                    return None
                data[field_name] = None
                continue

            normalized = self._normalize_evidence(raw_evidence)
            if normalized is None:
                if field_name == "entity_name":
                    return None
                data[field_name] = None
                evidence_map.pop(field_name, None)
                continue

            evidence_map[field_name] = normalized

        data["field_evidence"] = evidence_map
        return ExtractedEntity.model_validate(data)

    def _normalize_evidence(self, evidence: ExtractedFieldEvidence) -> ExtractedFieldEvidence | None:
        source_url = evidence.source_url.strip()
        if not source_url:
            return None

        normalized_snippet = re.sub(r"\s+", " ", evidence.evidence_snippet).strip()
        if not normalized_snippet:
            return None

        if len(normalized_snippet) > self._snippet_max_length:
            normalized_snippet = normalized_snippet[: self._snippet_max_length].rstrip()

        return ExtractedFieldEvidence(
            value=evidence.value,
            source_url=source_url,
            evidence_snippet=normalized_snippet,
        )
