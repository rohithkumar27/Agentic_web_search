from app.services.extractor import ExtractedEntity, ExtractedFieldEvidence
from app.services.scoring import ConfidenceScorer


def _entity_with_score_inputs(
    *,
    category: str | None,
    description: str | None,
    website: str | None,
    location: str | None,
    evidence_fields: dict[str, ExtractedFieldEvidence],
) -> ExtractedEntity:
    return ExtractedEntity(
        entity_name="Acme Health AI",
        category=category,
        description=description,
        website=website,
        location=location,
        key_attributes={},
        field_evidence=evidence_fields,
    )


def test_confidence_score_monotonicity_high_quality_beats_low_quality() -> None:
    scorer = ConfidenceScorer()

    low = _entity_with_score_inputs(
        category=None,
        description=None,
        website=None,
        location=None,
        evidence_fields={},
    )

    high = _entity_with_score_inputs(
        category="startup",
        description="Clinical AI company",
        website="https://acme.example.com",
        location="Boston, MA",
        evidence_fields={
            "entity_name": ExtractedFieldEvidence(
                value="Acme Health AI",
                source_url="https://news.a.com/post",
                evidence_snippet="Acme Health AI announced a launch in healthcare.",
            ),
            "category": ExtractedFieldEvidence(
                value="startup",
                source_url="https://report.b.org/acme",
                evidence_snippet="The startup is focused on clinical workflow automation.",
            ),
            "description": ExtractedFieldEvidence(
                value="Clinical AI company",
                source_url="https://db.c.net/acme",
                evidence_snippet="Acme is a clinical AI company serving hospitals.",
            ),
            "website": ExtractedFieldEvidence(
                value="https://acme.example.com",
                source_url="https://news.a.com/post",
                evidence_snippet="Official site: https://acme.example.com",
            ),
            "location": ExtractedFieldEvidence(
                value="Boston, MA",
                source_url="https://report.b.org/acme",
                evidence_snippet="Headquartered in Boston, MA.",
            ),
        },
    )

    assert scorer.score(high) > scorer.score(low)


def test_confidence_score_is_clamped_between_zero_and_one() -> None:
    scorer = ConfidenceScorer()

    contradictory = _entity_with_score_inputs(
        category="startup",
        description="A",
        website="https://a.example.com",
        location="NY",
        evidence_fields={
            "category": ExtractedFieldEvidence(
                value="government",
                source_url="https://a.example.com",
                evidence_snippet="x",
            ),
            "description": ExtractedFieldEvidence(
                value="B",
                source_url="https://b.example.com",
                evidence_snippet="y",
            ),
            "website": ExtractedFieldEvidence(
                value="https://different.example.com",
                source_url="https://c.example.com",
                evidence_snippet="z",
            ),
            "location": ExtractedFieldEvidence(
                value="SF",
                source_url="https://d.example.com",
                evidence_snippet="w",
            ),
        },
    )

    score = scorer.score(contradictory)
    assert 0.0 <= score <= 1.0


def test_source_diversity_improves_score() -> None:
    scorer = ConfidenceScorer()

    one_source = _entity_with_score_inputs(
        category="startup",
        description="Clinical AI company",
        website="https://acme.example.com",
        location="Boston, MA",
        evidence_fields={
            "entity_name": ExtractedFieldEvidence(
                value="Acme Health AI",
                source_url="https://news.a.com/post1",
                evidence_snippet="Acme Health AI launch details.",
            ),
            "description": ExtractedFieldEvidence(
                value="Clinical AI company",
                source_url="https://news.a.com/post2",
                evidence_snippet="Clinical AI company statement.",
            ),
        },
    )

    multi_source = _entity_with_score_inputs(
        category="startup",
        description="Clinical AI company",
        website="https://acme.example.com",
        location="Boston, MA",
        evidence_fields={
            "entity_name": ExtractedFieldEvidence(
                value="Acme Health AI",
                source_url="https://news.a.com/post1",
                evidence_snippet="Acme Health AI launch details.",
            ),
            "description": ExtractedFieldEvidence(
                value="Clinical AI company",
                source_url="https://blog.b.org/acme",
                evidence_snippet="Clinical AI company statement.",
            ),
            "location": ExtractedFieldEvidence(
                value="Boston, MA",
                source_url="https://data.c.net/acme",
                evidence_snippet="Headquartered in Boston, MA.",
            ),
        },
    )

    assert scorer.score(multi_source) > scorer.score(one_source)
