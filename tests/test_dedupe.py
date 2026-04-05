from app.services.dedupe import EntityDeduper
from app.services.extractor import ExtractedEntity, ExtractedFieldEvidence


def test_deduper_merges_by_shared_domain() -> None:
    entities = [
        ExtractedEntity(
            entity_name="Acme Health AI",
            category="startup",
            website="https://acmehealth.ai/about",
            description="Clinical AI tools",
            key_attributes={"founded": 2021},
            field_evidence={
                "entity_name": ExtractedFieldEvidence(
                    value="Acme Health AI",
                    source_url="https://news.example.com/a",
                    evidence_snippet="Acme Health AI raised funding.",
                )
            },
        ),
        ExtractedEntity(
            entity_name="Acme Health",
            category="company",
            website="https://www.acmehealth.ai/careers",
            description="Healthcare automation platform",
            key_attributes={"hq": "Boston"},
            field_evidence={
                "description": ExtractedFieldEvidence(
                    value="Healthcare automation platform",
                    source_url="https://blog.example.org/acme",
                    evidence_snippet="The company offers healthcare automation.",
                )
            },
        ),
    ]

    deduper = EntityDeduper()
    merged = deduper.dedupe(entities)

    assert len(merged) == 1
    entity = merged[0]
    assert entity.website == "https://acmehealth.ai"
    assert "source_urls" in entity.key_attributes
    assert set(entity.key_attributes["source_urls"]) == {
        "https://blog.example.org/acme",
        "https://news.example.com/a",
    }


def test_deduper_merges_by_name_similarity_when_domain_missing() -> None:
    entities = [
        ExtractedEntity(entity_name="PostgreSQL Database", description="Open source DB", field_evidence={}),
        ExtractedEntity(entity_name="Postgre SQL database", description="Object-relational database", field_evidence={}),
    ]

    deduper = EntityDeduper(name_similarity_threshold=0.85)
    merged = deduper.dedupe(entities)

    assert len(merged) == 1


def test_deduper_keeps_distinct_entities() -> None:
    entities = [
        ExtractedEntity(entity_name="PostgreSQL", category="database", field_evidence={}),
        ExtractedEntity(entity_name="ClickHouse", category="database", field_evidence={}),
    ]

    deduper = EntityDeduper()
    merged = deduper.dedupe(entities)

    assert len(merged) == 2
