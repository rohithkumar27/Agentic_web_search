from __future__ import annotations

import json

import pytest

from app.services.extractor import EntityExtractor, ExtractorError


class StubLLMClient:
    def __init__(self, responses: list[str | dict]):
        self._responses = responses
        self.calls = 0

    def complete(self, prompt: str, schema: dict) -> str | dict:
        self.calls += 1
        if not self._responses:
            raise AssertionError("No stub responses left")
        return self._responses.pop(0)


def test_extractor_recovers_after_malformed_output() -> None:
    client = StubLLMClient(
        responses=[
            "{not-json",
            {
                "entities": [
                    {
                        "entity_name": "Acme Health AI",
                        "category": "startup",
                        "description": "Clinical operations copilot.",
                        "website": "https://acme.example.com",
                        "location": "Boston, MA",
                        "key_attributes": {"founded": 2021},
                        "field_evidence": {
                            "entity_name": {
                                "value": "Acme Health AI",
                                "source_url": "https://news.example.com/acme",
                                "evidence_snippet": "Acme Health AI launched a clinical operations copilot.",
                            }
                        },
                    }
                ]
            },
        ]
    )

    extractor = EntityExtractor(client=client, max_retries=1)
    result = extractor.extract(
        query="AI startups in healthcare",
        source_url="https://news.example.com/acme",
        page_text="Acme Health AI launched a clinical operations copilot.",
    )

    assert client.calls == 2
    assert len(result.entities) == 1
    assert result.entities[0].entity_name == "Acme Health AI"


def test_extractor_raises_after_retry_exhausted() -> None:
    client = StubLLMClient(responses=["{not-json", "still-not-json"])
    extractor = EntityExtractor(client=client, max_retries=1)

    with pytest.raises(ExtractorError):
        extractor.extract(
            query="open source database tools",
            source_url="https://example.com/post",
            page_text="PostgreSQL and ClickHouse are popular databases.",
        )


def test_extractor_golden_output_contract() -> None:
    golden = {
        "entities": [
            {
                "entity_name": "PostgreSQL",
                "category": "database",
                "description": "Open-source relational database system.",
                "website": "https://www.postgresql.org",
                "location": None,
                "key_attributes": {"license": "PostgreSQL License"},
                "field_evidence": {
                    "description": {
                        "value": "Open-source relational database system.",
                        "source_url": "https://www.postgresql.org/about/",
                        "evidence_snippet": "PostgreSQL is a powerful, open source object-relational database system.",
                    }
                },
            }
        ]
    }

    client = StubLLMClient(responses=[json.dumps(golden)])
    extractor = EntityExtractor(client=client, max_retries=0)

    result = extractor.extract(
        query="open source database tools",
        source_url="https://www.postgresql.org/about/",
        page_text="PostgreSQL is a powerful, open source object-relational database system.",
    )

    assert result.model_dump() == golden


def test_extractor_accepts_code_fenced_json_payload() -> None:
    payload = """```json
{"entities":[{"entity_name":"Acme Health AI","field_evidence":{}}]}
```"""
    client = StubLLMClient(responses=[payload])
    extractor = EntityExtractor(client=client, max_retries=0)

    result = extractor.extract(
        query="AI startups in healthcare",
        source_url="https://example.com",
        page_text="Acme Health AI appears in this article.",
    )

    assert len(result.entities) == 1
    assert result.entities[0].entity_name == "Acme Health AI"


def test_extractor_truncates_oversized_evidence_snippet() -> None:
    long_snippet = "x" * 2000
    client = StubLLMClient(
        responses=[
            {
                "entities": [
                    {
                        "entity_name": "Acme Health AI",
                        "field_evidence": {
                            "entity_name": {
                                "value": "Acme Health AI",
                                "source_url": "https://example.com/source",
                                "evidence_snippet": long_snippet,
                            }
                        },
                    }
                ]
            }
        ]
    )
    extractor = EntityExtractor(client=client, max_retries=0)

    result = extractor.extract(
        query="AI startups",
        source_url="https://example.com/source",
        page_text="Acme Health AI appears in this article.",
    )

    snippet = result.entities[0].field_evidence["entity_name"].evidence_snippet
    assert len(snippet) == 500

def test_extractor_recovery_prompt_when_first_pass_empty() -> None:
    client = StubLLMClient(
        responses=[
            {"entities": []},
            {
                "entities": [
                    {
                        "entity_name": "Hippocratic AI",
                        "field_evidence": {
                            "entity_name": {
                                "value": "Hippocratic AI",
                                "source_url": "https://hippocraticai.com",
                                "evidence_snippet": "Hippocratic AI appears in the page.",
                            }
                        },
                    }
                ]
            },
        ]
    )

    extractor = EntityExtractor(client=client, max_retries=0)
    result = extractor.extract(
        query="AI startups in healthcare",
        source_url="https://hippocraticai.com",
        page_text="Hippocratic AI is a healthcare AI company.",
    )

    assert client.calls == 2
    assert len(result.entities) == 1
    assert result.entities[0].entity_name == "Hippocratic AI"
