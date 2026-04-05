from __future__ import annotations

from app.services.evidence_validator import EvidenceValidator
from app.services.extractor import ExtractedEntity, ExtractedFieldEvidence, ExtractionOutput


def test_validator_prunes_non_traceable_fields() -> None:
    output = ExtractionOutput(
        entities=[
            ExtractedEntity(
                entity_name="Acme Health AI",
                category="startup",
                description="Clinical AI company",
                website="https://acme.example.com",
                field_evidence={
                    "entity_name": ExtractedFieldEvidence(
                        value="Acme Health AI",
                        source_url="https://news.example.com/acme",
                        evidence_snippet="Acme Health AI launched a product.",
                    ),
                    "category": ExtractedFieldEvidence(
                        value="startup",
                        source_url="https://news.example.com/acme",
                        evidence_snippet="The startup announced funding.",
                    ),
                },
            )
        ]
    )

    validator = EvidenceValidator(snippet_max_length=100)
    validated = validator.validate_and_prune(output)
    entity = validated.entities[0]

    assert entity.category == "startup"
    assert entity.description is None
    assert entity.website is None


def test_validator_drops_entity_when_name_not_traceable() -> None:
    output = ExtractionOutput(
        entities=[
            ExtractedEntity(
                entity_name="Orphan Entity",
                category="company",
                field_evidence={},
            )
        ]
    )

    validator = EvidenceValidator()
    validated = validator.validate_and_prune(output)

    assert validated.entities == []


def test_validator_normalizes_and_truncates_snippet() -> None:
    messy_snippet = "  PostgreSQL\n\n is   an open-source   relational  database system.   "
    output = ExtractionOutput(
        entities=[
            ExtractedEntity(
                entity_name="PostgreSQL",
                description="Open-source relational database system.",
                field_evidence={
                    "entity_name": ExtractedFieldEvidence(
                        value="PostgreSQL",
                        source_url=" https://www.postgresql.org/about/ ",
                        evidence_snippet="PostgreSQL homepage",
                    ),
                    "description": ExtractedFieldEvidence(
                        value="Open-source relational database system.",
                        source_url="https://www.postgresql.org/about/",
                        evidence_snippet=messy_snippet,
                    ),
                },
            )
        ]
    )

    validator = EvidenceValidator(snippet_max_length=40)
    validated = validator.validate_and_prune(output)
    description_evidence = validated.entities[0].field_evidence["description"]

    assert description_evidence.source_url == "https://www.postgresql.org/about/"
    assert description_evidence.evidence_snippet == "PostgreSQL is an open-source relational"
