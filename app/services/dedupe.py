from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.services.extractor import ExtractedEntity, ExtractedFieldEvidence
from app.services.normalization import (
    normalize_category,
    normalize_domain,
    normalize_location,
    normalize_name,
    normalize_website,
)


@dataclass
class _Cluster:
    entities: list[ExtractedEntity] = field(default_factory=list)


class EntityDeduper:
    def __init__(self, name_similarity_threshold: float = 0.9) -> None:
        self._name_similarity_threshold = name_similarity_threshold

    def dedupe(self, entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        clusters: list[_Cluster] = []
        for entity in entities:
            cluster = self._find_cluster(clusters, entity)
            if cluster is None:
                cluster = _Cluster()
                clusters.append(cluster)
            cluster.entities.append(entity)

        return [self._merge_cluster(cluster) for cluster in clusters]

    def _find_cluster(self, clusters: list[_Cluster], candidate: ExtractedEntity) -> _Cluster | None:
        candidate_domain = normalize_domain(candidate.website)
        candidate_name = normalize_name(candidate.entity_name)

        for cluster in clusters:
            representative = cluster.entities[0]
            rep_domain = normalize_domain(representative.website)
            rep_name = normalize_name(representative.entity_name)

            if candidate_domain and rep_domain and candidate_domain == rep_domain:
                return cluster

            similarity = SequenceMatcher(a=candidate_name, b=rep_name).ratio()
            if similarity >= self._name_similarity_threshold:
                return cluster

        return None

    def _merge_cluster(self, cluster: _Cluster) -> ExtractedEntity:
        merged_evidence: dict[str, ExtractedFieldEvidence] = {}

        merged = ExtractedEntity(
            entity_name=self._pick_field(cluster.entities, "entity_name") or "",
            category=normalize_category(self._pick_field(cluster.entities, "category")),
            description=self._pick_field(cluster.entities, "description"),
            website=normalize_website(self._pick_field(cluster.entities, "website")),
            location=normalize_location(self._pick_field(cluster.entities, "location")),
            key_attributes=self._merge_key_attributes(cluster.entities),
            field_evidence=merged_evidence,
        )

        for field_name in ("entity_name", "category", "description", "website", "location"):
            best = self._pick_best_evidence(cluster.entities, field_name)
            if best is not None:
                merged.field_evidence[field_name] = best

        return merged

    def _pick_field(self, entities: list[ExtractedEntity], field_name: str) -> str | None:
        best_value: str | None = None
        best_score = -1
        for entity in entities:
            value = getattr(entity, field_name)
            if value is None:
                continue
            value_str = str(value)
            score = len(value_str)
            evidence = entity.field_evidence.get(field_name)
            if evidence is not None:
                score += len(evidence.evidence_snippet)
            if score > best_score:
                best_score = score
                best_value = value_str
        return best_value

    def _pick_best_evidence(self, entities: list[ExtractedEntity], field_name: str) -> ExtractedFieldEvidence | None:
        best: ExtractedFieldEvidence | None = None
        best_score = -1
        for entity in entities:
            evidence = entity.field_evidence.get(field_name)
            if evidence is None:
                continue
            score = len(evidence.evidence_snippet)
            if score > best_score:
                best = evidence
                best_score = score
        return best

    def _merge_key_attributes(self, entities: list[ExtractedEntity]) -> dict[str, object]:
        merged: dict[str, object] = {}
        source_urls: set[str] = set()

        for entity in entities:
            for key, value in entity.key_attributes.items():
                if key not in merged:
                    merged[key] = value
            for evidence in entity.field_evidence.values():
                source_urls.add(evidence.source_url)

        if source_urls:
            merged["source_urls"] = sorted(source_urls)

        return merged
